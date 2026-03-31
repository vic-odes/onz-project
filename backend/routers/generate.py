import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.project import ProjectCreate
from services import ai_service, docx_service
from database import save_project
import io
import json

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/")
async def generate_document(project: ProjectCreate):
    # Extraire les PDFs du payload — ils ne doivent pas être sérialisés dans le prompt ni en base
    project_dict = project.model_dump()
    reference_pdfs = project_dict.pop("reference_pdfs", None) or []

    logger.info(
        "Génération démarrée — projet=%r pays=%r secteur=%r bailleur=%r pdfs=%d",
        project.nom, project_dict.get("pays"), project_dict.get("secteur"),
        project_dict.get("bailleur"), len(reference_pdfs),
    )

    try:
        # 1. Génération IA via LiteLLM
        generated = await ai_service.generate_project_content(project_dict, reference_pdfs or None)
        logger.info("Génération IA réussie — clés reçues: %s", list(generated.keys()))
    except json.JSONDecodeError as e:
        logger.exception("JSON invalide retourné par le modèle")
        raise HTTPException(
            status_code=500,
            detail=f"Le modèle IA a retourné un JSON invalide : {str(e)}"
        )
    except Exception as e:
        logger.exception("Erreur lors de la génération IA")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération IA : {str(e)}"
        )

    try:
        # 2. Création du fichier Word
        docx_bytes = docx_service.create_word_document(project_dict, generated)
        logger.info("Document Word créé — taille=%d octets", len(docx_bytes))
    except Exception as e:
        logger.exception("Erreur lors de la création du document Word")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création du document Word : {str(e)}"
        )

    # 3. Sauvegarde en base SQLite (non bloquant sur erreur)
    try:
        save_project(project_dict, generated)
        logger.debug("Projet sauvegardé en base")
    except Exception:
        logger.exception("Erreur sauvegarde SQLite (non bloquant)")

    # 4. Retour du fichier
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project.nom)
    filename = f"{safe_name.replace(' ', '_')}_ONZ.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
