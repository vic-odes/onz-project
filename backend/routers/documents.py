import io
import base64
import json
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

from dependencies import get_current_user
from models.user import User
from services import llm_client
from services.pdf_validation import validate_pdf_b64, PdfValidationError

logger = logging.getLogger(__name__)
router = APIRouter()

PREFILL_PROMPT = """Analyse ce document PDF et extrais les informations du projet de développement qu'il contient.

Retourne UNIQUEMENT un objet JSON avec les champs que tu trouves clairement dans le document, parmi :
- nom : nom du projet (string)
- pays : pays ou zone d'intervention (string)
- secteur : secteur parmi Santé, Éducation, Agriculture, Environnement, Eau & Assainissement, Gouvernance, Protection sociale, Autre (string)
- bailleur : nom du bailleur de fonds (string)
- probleme_principal : problème principal décrit dans le document (string)
- objectif_global : objectif global ou impact visé (string)
- objectifs_specifiques : liste d'objectifs spécifiques (array de strings)
- population_cible : population ciblée (string)
- nombre_beneficiaires : nombre de bénéficiaires (integer)
- duree_mois : durée du projet en mois (integer)
- budget_total : budget total en USD (number)
- source_financement : source de financement principale (string)
- contraintes : contraintes identifiées (string)
- risques_identifies : risques identifiés (string)

Règles strictes :
- N'invente RIEN. N'inclus un champ QUE si l'information est clairement et explicitement présente.
- Si tu n'es pas sûr d'une valeur, ne l'inclus pas.
- Réponds UNIQUEMENT en JSON valide, sans markdown ni backticks.
"""

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
            {"type": "text", "text": PREFILL_PROMPT},
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
        {"role": "user", "content": f"{PREFILL_PROMPT}\n\nContenu du document :\n{text}"},
    ]
    try:
        return await _call_prefill_llm(fallback_messages)
    except json.JSONDecodeError:
        logger.exception("Prefill fallback JSON invalide")
        raise HTTPException(
            status_code=500,
            detail="Extraction impossible : le modèle n'a pas retourné de JSON valide.",
        )
