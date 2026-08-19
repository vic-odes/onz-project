import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from dependencies import get_current_user
from models.financement import RechercheFinancement
from models.project import Project
from models.user import User
from schemas.financement import (
    RECHERCHE_BAILLEUR_LABEL,
    ImporterProjetRequest,
    RechercheFinancementResponse,
    RechercheFinancementSummary,
    ResultatsFinancement,
)
from services import financement_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _owned_project_or_404(db: Session, project_id: int, user_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    return project


def _owned_recherche_or_404(db: Session, recherche_id: int, user_id: int) -> RechercheFinancement:
    recherche = (
        db.query(RechercheFinancement)
        .filter(RechercheFinancement.id == recherche_id, RechercheFinancement.user_id == user_id)
        .first()
    )
    if not recherche:
        raise HTTPException(status_code=404, detail="Recherche non trouvée")
    return recherche


def _to_response(recherche: RechercheFinancement, project_nom: str) -> RechercheFinancementResponse:
    return RechercheFinancementResponse(
        id=recherche.id,
        project_id=recherche.project_id,
        project_nom=project_nom,
        recherche_live=recherche.recherche_live,
        status=recherche.status,
        erreur=recherche.erreur,
        created_at=recherche.created_at,
        resultats=ResultatsFinancement.model_validate(json.loads(recherche.resultats)),
    )


def _project_data(project: Project) -> dict:
    return {
        "nom": project.nom,
        "pays": project.pays,
        "secteur": project.secteur,
        "probleme_principal": project.probleme_principal,
        "objectif_global": project.objectif_global,
        "budget_total": project.budget_total,
        "duree_mois": project.duree_mois,
    }


async def _executer_recherche_en_arriere_plan(recherche_id: int, project_data: dict) -> None:
    """Exécute l'appel LLM (potentiellement long — recherche web incluse) et
    met à jour la ligne à la fin. Tourne après l'envoi de la réponse HTTP —
    utilise sa propre session DB, indépendante de celle de la requête (déjà
    fermée à ce stade)."""
    db = SessionLocal()
    try:
        recherche = db.query(RechercheFinancement).filter(RechercheFinancement.id == recherche_id).first()
        if not recherche:
            logger.error("Recherche %d introuvable au moment de l'exécution en arrière-plan", recherche_id)
            return
        try:
            resultats, recherche_live = await financement_service.rechercher_financements(project_data)
        except Exception as e:
            logger.exception("Recherche de financement %d — échec en arrière-plan", recherche_id)
            recherche.status = "erreur"
            recherche.erreur = str(e)
            db.commit()
            return

        recherche.resultats = json.dumps(resultats.model_dump(), ensure_ascii=False)
        recherche.recherche_live = recherche_live
        recherche.status = "termine"
        db.commit()
        logger.info("Recherche de financement %d terminée (%d opportunité(s))", recherche_id, len(resultats.opportunites))
    finally:
        db.close()


def _demarrer_recherche(
    db: Session, background_tasks: BackgroundTasks, current_user: User, project: Project
) -> RechercheFinancementResponse:
    """Crée la ligne en `status="en_cours"` et programme la recherche LLM en
    tâche de fond. Retourne immédiatement — le frontend sonde `GET /{id}`."""
    project_data = _project_data(project)
    recherche = RechercheFinancement(
        user_id=current_user.id,
        project_id=project.id,
        criteres=json.dumps(project_data, ensure_ascii=False),
        resultats="{}",
        recherche_live=False,
        status="en_cours",
    )
    db.add(recherche)
    db.commit()
    db.refresh(recherche)

    background_tasks.add_task(_executer_recherche_en_arriere_plan, recherche.id, project_data)

    return _to_response(recherche, project.nom)


@router.post("/rechercher/{project_id}", response_model=RechercheFinancementResponse)
def rechercher_financement(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Démarre une recherche de financements pour un projet déjà monté (en
    arrière-plan) et renvoie immédiatement son état initial."""
    project = _owned_project_or_404(db, project_id, current_user.id)
    return _demarrer_recherche(db, background_tasks, current_user, project)


@router.post("/importer", response_model=RechercheFinancementResponse)
def importer_et_rechercher(
    payload: ImporterProjetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crée un projet minimal (sans document généré) à partir de champs extraits
    d'un PDF externe — via /api/documents/prefill côté frontend — et démarre
    immédiatement une recherche de financement en arrière-plan. Permet de
    rechercher un financement pour un projet monté hors de l'application."""
    project = Project(
        user_id=current_user.id,
        nom=payload.nom,
        pays=payload.pays,
        secteur=payload.secteur or "Non précisé",
        bailleur=RECHERCHE_BAILLEUR_LABEL,
        probleme_principal=payload.probleme_principal,
        objectif_global=payload.objectif_global,
        budget_total=payload.budget_total,
        duree_mois=payload.duree_mois,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return _demarrer_recherche(db, background_tasks, current_user, project)


@router.get("/{recherche_id}", response_model=RechercheFinancementResponse)
def get_recherche(
    recherche_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """À sonder par le frontend tant que `status == "en_cours"`."""
    recherche = _owned_recherche_or_404(db, recherche_id, current_user.id)
    project = db.query(Project).filter(Project.id == recherche.project_id).first()
    return _to_response(recherche, project.nom if project else "")


@router.get("/projet/{project_id}", response_model=list[RechercheFinancementSummary])
def list_recherches_pour_projet(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recherches passées pour un projet, les plus récentes d'abord — évite de
    relancer un appel LLM pour simplement revoir des résultats déjà obtenus."""
    _owned_project_or_404(db, project_id, current_user.id)
    recherches = (
        db.query(RechercheFinancement)
        .filter(RechercheFinancement.project_id == project_id, RechercheFinancement.user_id == current_user.id)
        .order_by(RechercheFinancement.created_at.desc())
        .all()
    )
    summaries = []
    for r in recherches:
        resultats = json.loads(r.resultats)
        summaries.append(
            RechercheFinancementSummary(
                id=r.id,
                recherche_live=r.recherche_live,
                status=r.status,
                created_at=r.created_at,
                nb_opportunites=len(resultats.get("opportunites", [])),
                resume=resultats.get("resume", ""),
            )
        )
    return summaries
