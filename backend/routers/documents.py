import os
import io
import base64
import json
import logging
import litellm
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(override=True)

litellm.drop_params = True

logger = logging.getLogger(__name__)
router = APIRouter()
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

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


class PrefillRequest(BaseModel):
    pdf_b64: str


async def _call_prefill(messages: list, extra: dict) -> dict:
    logger.debug("Appel prefill LLM — modèle=%s", MODEL)
    try:
        response = await litellm.acompletion(
            model=MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.1,
            **extra,
        )
    except Exception:
        logger.exception("Erreur lors de l'appel LiteLLM pour prefill (modèle=%s)", MODEL)
        raise
    content = response.choices[0].message.content
    logger.debug("Réponse prefill — finish_reason=%s content_len=%s",
                 response.choices[0].finish_reason,
                 len(content) if content else "None")
    if not content:
        logger.error("Prefill : modèle a retourné un contenu vide")
        raise ValueError("Le modèle n'a retourné aucun contenu.")
    raw = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    if not raw:
        logger.error("Prefill : contenu vide après nettoyage. Brut: %r", content[:200])
        raise ValueError("Le modèle a retourné une réponse vide après nettoyage.")
    try:
        result = json.loads(raw)
        logger.info("Prefill réussi — %d champs extraits", len(result))
        return result
    except json.JSONDecodeError:
        logger.error("Prefill JSON invalide. Début: %r", raw[:500])
        raise


@router.post("/prefill")
async def prefill_from_pdf(payload: PrefillRequest):
    """
    Extrait les informations structurées d'un PDF pour pré-remplir le formulaire.
    Essaie d'abord en natif (vision), bascule sur extraction texte si le modèle ne supporte pas.
    """
    extra = {}
    if os.getenv("AZURE_API_KEY"):
        extra["api_key"] = os.getenv("AZURE_API_KEY")
    if os.getenv("AZURE_API_BASE"):
        extra["api_base"] = os.getenv("AZURE_API_BASE")
    if os.getenv("AZURE_API_VERSION"):
        extra["api_version"] = os.getenv("AZURE_API_VERSION")

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
        data = await _call_prefill(messages, extra)
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
            data = await _call_prefill(fallback_messages, extra)
        except json.JSONDecodeError:
            logger.exception("Prefill fallback JSON invalide")
            raise HTTPException(status_code=500, detail="Extraction impossible : le modèle n'a pas retourné de JSON valide.")

    return data
