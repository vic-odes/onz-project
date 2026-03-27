from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.project import ProjectCreate
from services import ai_service, docx_service
from database import save_project
import io
import json

router = APIRouter()


@router.post("/")
async def generate_document(project: ProjectCreate):
    try:
        # 1. Génération IA via LiteLLM
        generated = await ai_service.generate_project_content(project.model_dump())
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Le modèle IA a retourné un JSON invalide : {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération IA : {str(e)}"
        )

    try:
        # 2. Création du fichier Word
        docx_bytes = docx_service.create_word_document(project.model_dump(), generated)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création du document Word : {str(e)}"
        )

    # 3. Sauvegarde en base SQLite (non bloquant sur erreur)
    try:
        save_project(project.model_dump(), generated)
    except Exception:
        pass  # La sauvegarde est optionnelle, ne pas bloquer le téléchargement

    # 4. Retour du fichier
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project.nom)
    filename = f"{safe_name.replace(' ', '_')}_ONZ.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
