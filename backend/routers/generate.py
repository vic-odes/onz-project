import io
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from database import save_project
from http_utils import content_disposition_attachment
from dependencies import get_current_user
from models.user import User
from schemas.evaluation import Evaluation
from schemas.project import ProjectCreate
from services import ai_service, docx_service, llm_client, prompts

logger = logging.getLogger(__name__)
router = APIRouter()

# Évaluation : sortie compacte (analyse + notation), température basse pour la stabilité.
_EVALUATION_MAX_TOKENS = 2500
_EVALUATION_TEMPERATURE = 0.2


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

    try:
        save_project(project_dict, generated, current_user.id, docx_bytes)
        logger.debug("Projet et document DOCX sauvegardés")
    except Exception:
        logger.exception("Erreur sauvegarde SQLite (non bloquant)")

    docx_name = f"{(project.nom or '').strip() or 'Projet'}_ONZ.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": content_disposition_attachment(docx_name)},
    )


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
