import io
import json
import logging
from urllib.parse import quote

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

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": _content_disposition(project.nom)},
    )


def _content_disposition(nom: str) -> str:
    """En-tête Content-Disposition robuste (RFC 6266) pour le téléchargement du .docx.

    Les en-têtes HTTP sont limités à l'ASCII/latin-1 : un nom de projet accentué
    (« Café », « Éducation ») ou non-latin casse la réponse si on l'injecte brut
    (`str.isalnum()` est Unicode-aware et laisse passer les accents). On fournit
    donc deux formes, comme le fait Starlette pour `FileResponse` :
    - `filename=`  : repli ASCII pur (tout caractère non-ASCII → `_`) ;
    - `filename*=` : version UTF-8 encodée en pourcentage (RFC 5987), lue en
      priorité par les navigateurs modernes, qui préserve les accents.
    """
    base = f"{(nom or '').strip() or 'Projet'}_ONZ.docx"
    ascii_fallback = "".join(
        c if (c.isascii() and (c.isalnum() or c in " _-.")) else "_" for c in base
    ).replace(" ", "_")
    utf8_encoded = quote(base, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{utf8_encoded}"
