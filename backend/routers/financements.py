import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database import get_db
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
        created_at=recherche.created_at,
        resultats=ResultatsFinancement.model_validate(json.loads(recherche.resultats)),
    )


async def _rechercher_et_persister(
    db: Session, current_user: User, project: Project
) -> RechercheFinancementResponse:
    """Lance la recherche LLM pour `project`, persiste le résultat, et renvoie la
    réponse API. Partagé par `/rechercher/{project_id}` et `/importer`."""
    project_data = {
        "nom": project.nom,
        "pays": project.pays,
        "secteur": project.secteur,
        "probleme_principal": project.probleme_principal,
        "objectif_global": project.objectif_global,
        "budget_total": project.budget_total,
        "duree_mois": project.duree_mois,
    }

    try:
        resultats, recherche_live = await financement_service.rechercher_financements(project_data)
    except json.JSONDecodeError as e:
        logger.exception("Recherche de financement — JSON invalide retourné par le modèle")
        raise HTTPException(status_code=502, detail=f"Le modèle IA a retourné un JSON invalide : {str(e)}")
    except ValidationError as e:
        missing = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
        logger.error("Recherche de financement — sortie invalide : %s", missing)
        raise HTTPException(
            status_code=502,
            detail=f"Le modèle IA a retourné une réponse incomplète (champ(s) : {', '.join(missing)}). Réessayez.",
        )
    except Exception as e:
        logger.exception("Erreur lors de la recherche de financement")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche de financement : {str(e)}")

    recherche = RechercheFinancement(
        user_id=current_user.id,
        project_id=project.id,
        criteres=json.dumps(project_data, ensure_ascii=False),
        resultats=json.dumps(resultats.model_dump(), ensure_ascii=False),
        recherche_live=recherche_live,
    )
    db.add(recherche)
    db.commit()
    db.refresh(recherche)

    return _to_response(recherche, project.nom)


@router.post("/rechercher/{project_id}", response_model=RechercheFinancementResponse)
async def rechercher_financement(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lance une recherche de financements pour un projet déjà monté et la persiste."""
    project = _owned_project_or_404(db, project_id, current_user.id)
    return await _rechercher_et_persister(db, current_user, project)


@router.post("/importer", response_model=RechercheFinancementResponse)
async def importer_et_rechercher(
    payload: ImporterProjetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crée un projet minimal (sans document généré) à partir de champs extraits
    d'un PDF externe — via /api/documents/prefill côté frontend — et lance
    immédiatement une recherche de financement. Permet de rechercher un
    financement pour un projet monté hors de l'application."""
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

    return await _rechercher_et_persister(db, current_user, project)


@router.get("/{recherche_id}", response_model=RechercheFinancementResponse)
def get_recherche(
    recherche_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
                created_at=r.created_at,
                nb_opportunites=len(resultats.get("opportunites", [])),
                resume=resultats.get("resume", ""),
            )
        )
    return summaries
