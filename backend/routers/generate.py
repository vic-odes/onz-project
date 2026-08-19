import io
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database import SessionLocal, get_db, save_project
from http_utils import content_disposition_attachment
from dependencies import get_current_user
from models.generation import GenerationJob
from models.user import User
from schemas.evaluation import Evaluation
from schemas.generation_job import GenerationJobResponse
from schemas.note_conceptuelle import NoteConceptuelle
from schemas.project import ProjectCreate
from services import ai_service, docx_service, llm_client, prompts

logger = logging.getLogger(__name__)
router = APIRouter()

# Évaluation : sortie compacte (analyse + notation), température basse pour la stabilité.
_EVALUATION_MAX_TOKENS = 2500
_EVALUATION_TEMPERATURE = 0.2

# Note conceptuelle : document court (2-4 pages), un peu plus de tokens pour le narratif.
_NOTE_MAX_TOKENS = 4000
_NOTE_TEMPERATURE = 0.3


@router.post("/")
async def generate_document(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
):
    """Génère le document : appel LLM, mise en forme DOCX, persistance, puis renvoi du .docx."""
    project_dict = project.model_dump()
    reference_pdfs = project_dict.pop("reference_pdfs", None) or []

    # En demande de financement, la durabilité/pérennisation est un attendu du bailleur :
    # on force la section, quel que soit le flag coché par l'utilisateur.
    if project_dict.get("type_dossier") == "financement":
        project_dict["inclure_perennisation"] = True

    logger.info(
        "Génération démarrée — user=%d projet=%r type=%s pays=%r secteur=%r bailleur=%r pdfs=%d",
        current_user.id, project.nom, project_dict.get("type_dossier"),
        project_dict.get("pays"), project_dict.get("secteur"),
        project_dict.get("bailleur"), len(reference_pdfs),
    )

    try:
        generated = await ai_service.generate_project_content(project_dict, reference_pdfs or None)
        logger.info("Génération IA réussie — clés reçues: %s", list(generated.keys()))
    except json.JSONDecodeError as e:
        logger.exception("JSON invalide retourné par le modèle")
        raise HTTPException(status_code=502, detail=f"Le modèle IA a retourné un JSON invalide : {str(e)}")
    except ValidationError as e:
        missing = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
        logger.error("Sortie LLM invalide — champs problématiques : %s", missing)
        raise HTTPException(
            status_code=502,
            detail=(
                "Le modèle IA a retourné une réponse incomplète "
                f"(champ(s) problématique(s) : {', '.join(missing)}). Réessayez."
            ),
        )
    except Exception as e:
        logger.exception("Erreur lors de la génération IA")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération IA : {str(e)}")

    try:
        docx_bytes = docx_service.create_word_document(project_dict, generated)
        logger.info("Document Word créé — taille=%d octets", len(docx_bytes))
    except Exception as e:
        logger.exception("Erreur lors de la création du document Word")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du document Word : {str(e)}")

    project_id: int | None = None
    try:
        saved = save_project(project_dict, generated, current_user.id, docx_bytes)
        project_id = saved.id
        logger.debug("Projet et document DOCX sauvegardés — id=%d", project_id)
    except Exception:
        logger.exception("Erreur sauvegarde SQLite (non bloquant)")

    docx_name = f"{(project.nom or '').strip() or 'Projet'}_ONZ.docx"
    headers = {"Content-Disposition": content_disposition_attachment(docx_name)}
    if project_id is not None:
        # Permet au frontend d'enchaîner sur une recherche de financement (bailleur
        # « à déterminer automatiquement ») sans avoir à relister les projets.
        headers["X-Project-Id"] = str(project_id)
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


async def _executer_generation_en_arriere_plan(
    job_id: int, project_dict: dict, reference_pdfs: list, user_id: int
) -> None:
    """Exécute l'appel LLM + mise en forme DOCX + persistance en tâche de fond
    (potentiellement long — PDFs natifs inclus) et met à jour la ligne à la
    fin. Tourne après l'envoi de la réponse HTTP — utilise sa propre session
    DB, indépendante de celle de la requête (déjà fermée à ce stade)."""
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            logger.error("Job de génération %d introuvable au moment de l'exécution en arrière-plan", job_id)
            return

        try:
            generated = await ai_service.generate_project_content(project_dict, reference_pdfs or None)
        except json.JSONDecodeError as e:
            logger.exception("Génération %d — JSON invalide retourné par le modèle", job_id)
            job.status = "erreur"
            job.erreur = f"Le modèle IA a retourné un JSON invalide : {str(e)}"
            db.commit()
            return
        except ValidationError as e:
            missing = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
            logger.error("Génération %d — sortie LLM invalide — champs problématiques : %s", job_id, missing)
            job.status = "erreur"
            job.erreur = (
                "Le modèle IA a retourné une réponse incomplète "
                f"(champ(s) problématique(s) : {', '.join(missing)}). Réessayez."
            )
            db.commit()
            return
        except Exception as e:
            logger.exception("Génération %d — erreur lors de la génération IA", job_id)
            job.status = "erreur"
            job.erreur = f"Erreur lors de la génération IA : {str(e)}"
            db.commit()
            return

        try:
            docx_bytes = docx_service.create_word_document(project_dict, generated)
        except Exception as e:
            logger.exception("Génération %d — erreur lors de la création du document Word", job_id)
            job.status = "erreur"
            job.erreur = f"Erreur lors de la création du document Word : {str(e)}"
            db.commit()
            return

        try:
            saved = save_project(project_dict, generated, user_id, docx_bytes)
            saved_id = saved.id
        except Exception as e:
            logger.exception("Génération %d — erreur sauvegarde SQLite", job_id)
            job.status = "erreur"
            job.erreur = f"Erreur lors de la sauvegarde du projet : {str(e)}"
            db.commit()
            return

        job.project_id = saved_id
        job.status = "termine"
        db.commit()
        logger.info("Génération %d terminée — projet %d créé", job_id, saved_id)
    finally:
        db.close()


@router.post("/demarrer", response_model=GenerationJobResponse)
def demarrer_generation(
    project: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Démarre la génération du document en arrière-plan et renvoie
    immédiatement un identifiant de suivi. Évite qu'une requête bloquante de
    plusieurs dizaines de secondes (voire minutes avec PDFs natifs) ne soit
    coupée par le navigateur ou un proxy (ex. timeout d'ingress, mise en veille
    de l'appareil). Le frontend sonde `GET /api/generate/etat/{id}`, puis
    télécharge via `GET /api/projects/{project_id}/download` une fois
    `status == "termine"`."""
    project_dict = project.model_dump()
    reference_pdfs = project_dict.pop("reference_pdfs", None) or []

    if project_dict.get("type_dossier") == "financement":
        project_dict["inclure_perennisation"] = True

    logger.info(
        "Génération démarrée (arrière-plan) — user=%d projet=%r type=%s pays=%r secteur=%r bailleur=%r pdfs=%d",
        current_user.id, project.nom, project_dict.get("type_dossier"),
        project_dict.get("pays"), project_dict.get("secteur"),
        project_dict.get("bailleur"), len(reference_pdfs),
    )

    job = GenerationJob(user_id=current_user.id, status="en_cours")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _executer_generation_en_arriere_plan, job.id, project_dict, reference_pdfs, current_user.id
    )
    return job


@router.get("/etat/{job_id}", response_model=GenerationJobResponse)
def etat_generation(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """À sonder par le frontend tant que `status == "en_cours"`."""
    job = (
        db.query(GenerationJob)
        .filter(GenerationJob.id == job_id, GenerationJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Génération non trouvée")
    return job


@router.post("/evaluation", response_model=Evaluation)
async def evaluate_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
):
    """Évalue un projet sans le générer : analyse du bailleur ciblé + score de
    compatibilité (#1) et notation type comité de sélection + recommandations (#14).

    Réutilise le pattern LLM → JSON → validation Pydantic (comme /prefill). Aucune
    persistance : c'est un retour d'aide à la décision, calculé à la volée.
    """
    project_dict = project.model_dump()
    # Les PDFs de référence ne sont pas utiles pour l'évaluation du concept.
    project_dict.pop("reference_pdfs", None)

    logger.info(
        "Évaluation démarrée — user=%d projet=%r bailleur=%r",
        current_user.id, project.nom, project_dict.get("bailleur"),
    )

    user_prompt = prompts.load("user_evaluation").format(
        project_data_json=json.dumps(project_dict, ensure_ascii=False, indent=2),
    )
    messages = [
        {"role": "system", "content": prompts.load("system_evaluation")},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await llm_client.call_llm(
            messages,
            max_tokens=_EVALUATION_MAX_TOKENS,
            temperature=_EVALUATION_TEMPERATURE,
        )
        result = llm_client.parse_json_response(raw)
    except json.JSONDecodeError as e:
        logger.exception("Évaluation — JSON invalide retourné par le modèle")
        raise HTTPException(status_code=502, detail=f"Le modèle IA a retourné un JSON invalide : {str(e)}")
    except Exception as e:
        logger.exception("Erreur lors de l'évaluation IA")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'évaluation IA : {str(e)}")

    try:
        evaluation = Evaluation.model_validate(result)
    except ValidationError as e:
        missing = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
        logger.error("Sortie d'évaluation invalide — champs problématiques : %s", missing)
        raise HTTPException(
            status_code=502,
            detail=(
                "Le modèle IA a retourné une évaluation incomplète "
                f"(champ(s) problématique(s) : {', '.join(missing)}). Réessayez."
            ),
        )

    logger.info(
        "Évaluation réussie — compatibilité=%d%% score=%.0f/100",
        evaluation.analyse_bailleur.score_compatibilite,
        evaluation.notation.score_total_sur_100,
    )
    return evaluation


@router.post("/note-conceptuelle")
async def generate_note_conceptuelle(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
):
    """Génère une note conceptuelle autonome (concept note, 2-4 pages) au format
    bailleur et renvoie directement le .docx. Livrable à la demande, non persisté."""
    project_dict = project.model_dump()
    project_dict.pop("reference_pdfs", None)

    logger.info(
        "Note conceptuelle démarrée — user=%d projet=%r bailleur=%r",
        current_user.id, project.nom, project_dict.get("bailleur"),
    )

    user_prompt = prompts.load("user_note_conceptuelle").format(
        project_data_json=json.dumps(project_dict, ensure_ascii=False, indent=2),
    )
    messages = [
        {"role": "system", "content": prompts.load("system_note_conceptuelle")},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await llm_client.call_llm(
            messages,
            max_tokens=_NOTE_MAX_TOKENS,
            temperature=_NOTE_TEMPERATURE,
        )
        result = llm_client.parse_json_response(raw)
    except json.JSONDecodeError as e:
        logger.exception("Note conceptuelle — JSON invalide retourné par le modèle")
        raise HTTPException(status_code=502, detail=f"Le modèle IA a retourné un JSON invalide : {str(e)}")
    except Exception as e:
        logger.exception("Erreur lors de la génération de la note conceptuelle")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération de la note conceptuelle : {str(e)}")

    try:
        note = NoteConceptuelle.model_validate(result)
    except ValidationError as e:
        missing = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
        logger.error("Note conceptuelle invalide — champs problématiques : %s", missing)
        raise HTTPException(
            status_code=502,
            detail=(
                "Le modèle IA a retourné une note conceptuelle incomplète "
                f"(champ(s) problématique(s) : {', '.join(missing)}). Réessayez."
            ),
        )

    try:
        docx_bytes = docx_service.create_note_conceptuelle_document(project_dict, note.model_dump())
    except Exception as e:
        logger.exception("Erreur création docx note conceptuelle")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du document : {str(e)}")

    filename = f"{(project.nom or 'Projet').strip()}_note_conceptuelle_ONZ.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": content_disposition_attachment(filename)},
    )
