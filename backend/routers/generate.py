import io
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from database import save_project
from dependencies import get_current_user
from models.user import User
from schemas.project import ProjectCreate
from services import ai_service, docx_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/")
async def generate_document(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
):
    """Génère le document : appel LLM, mise en forme DOCX, persistance, puis renvoi du .docx."""
    project_dict = project.model_dump()
    reference_pdfs = project_dict.pop("reference_pdfs", None) or []

    logger.info(
        "Génération démarrée — user=%d projet=%r pays=%r secteur=%r bailleur=%r pdfs=%d",
        current_user.id, project.nom, project_dict.get("pays"), project_dict.get("secteur"),
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

    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project.nom)
    filename = f"{safe_name.replace(' ', '_')}_ONZ.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
