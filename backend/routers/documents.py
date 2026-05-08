import io
import base64
import json
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

from dependencies import get_current_user
from models.user import User
from services import llm_client, prompts
from services.pdf_validation import validate_pdf_b64, PdfValidationError

logger = logging.getLogger(__name__)
router = APIRouter()

# Prompt externalisé dans backend/prompts/prefill.md (chargement paresseux + cache).
def _prefill_prompt() -> str:
    return prompts.load("prefill")

_PREFILL_MAX_TOKENS = 2000
_PREFILL_TEMPERATURE = 0.1


class PrefillRequest(BaseModel):
    pdf_b64: str

    @field_validator("pdf_b64")
    @classmethod
    def _check_pdf(cls, v: str) -> str:
        try:
            validate_pdf_b64(v)
        except PdfValidationError as e:
            raise ValueError(str(e))
        return v


async def _call_prefill_llm(messages: list) -> dict:
    """Wrapper local : low temp + tokens limités, sortie JSON parsée."""
    raw = await llm_client.call_llm(
        messages,
        max_tokens=_PREFILL_MAX_TOKENS,
        temperature=_PREFILL_TEMPERATURE,
    )
    result = llm_client.parse_json_response(raw)
    logger.info("Prefill réussi — %d champs extraits", len(result))
    return result


@router.post("/prefill")
async def prefill_from_pdf(
    payload: PrefillRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Extrait les informations structurées d'un PDF pour pré-remplir le formulaire.
    Essaie d'abord en natif (vision), bascule sur extraction texte si le modèle ne supporte pas.
    """
    pdf_size_kb = len(payload.pdf_b64) * 3 // 4 // 1024
    logger.info("Prefill depuis PDF — taille estimée ~%d Ko", pdf_size_kb)

    # Tentative avec document natif (Claude vision)
    messages = [
        {"role": "user", "content": [
            {"type": "document", "source": {
                "type": "base64", "media_type": "application/pdf", "data": payload.pdf_b64,
            }},
            {"type": "text", "text": _prefill_prompt()},
        ]},
    ]

    try:
        return await _call_prefill_llm(messages)
    except Exception as e:
        logger.warning("Prefill natif échoué (%s: %s) — bascule sur extraction texte", type(e).__name__, e)

    # Fallback : extraction texte avec pypdf
    try:
        import pypdf
        pdf_bytes = base64.b64decode(payload.pdf_b64)
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        logger.info("Texte extrait par pypdf — %d caractères, %d pages", len(text), len(reader.pages))
    except Exception as ex:
        logger.exception("Impossible de lire le PDF avec pypdf")
        raise HTTPException(status_code=400, detail=f"Impossible de lire le PDF : {ex}")

    fallback_messages = [
        {"role": "user", "content": f"{_prefill_prompt()}\n\nContenu du document :\n{text}"},
    ]
    try:
        return await _call_prefill_llm(fallback_messages)
    except json.JSONDecodeError:
        logger.exception("Prefill fallback JSON invalide")
        raise HTTPException(
            status_code=500,
            detail="Extraction impossible : le modèle n'a pas retourné de JSON valide.",
        )
