import io
import base64
import json
import logging
import os
from typing import Optional

from services import llm_client, prompts

logger = logging.getLogger(__name__)

# Limite du texte extrait pour éviter le dépassement de contexte (indépendante du modèle)
_MAX_EXTRACTED_CHARS = 3000


def _compute_max_tokens(supports_native_pdf: bool) -> int:
    """Retourne le plafond de tokens à passer au modèle.

    Défaut : 16000. Justification :
    - Le JSON complet d'un projet pèse 4-8k tokens de sortie utile.
    - Les modèles à raisonnement (GPT-5, o1, o3…) consomment en plus 2-6k
      tokens de raisonnement *invisibles* imputés sur la même limite.
    - Marge de sécurité pour les projets longs (résumé exécutif + note
      conceptuelle activés, plusieurs PDFs de référence).

    `LLM_MAX_TOKENS` (env) reste prioritaire pour ajuster vers le bas si
    le plan/la licence du modèle est plus restrictif (Mistral Small 4096,
    GPT-3.5 Turbo, etc.).
    """
    env_val = os.getenv("LLM_MAX_TOKENS")
    if env_val:
        return int(env_val)
    return 16000


# Les prompts vivent dans backend/prompts/*.md (chargement paresseux + cache).
def _system_prompt() -> str:
    return prompts.load("system_generate")


def _build_user_prompt(project_data: dict, has_references: bool) -> str:
    template = prompts.load("user_generate")
    reference_note = "\n" + prompts.load("reference_note") + "\n" if has_references else ""
    return template.format(
        project_data_json=json.dumps(project_data, ensure_ascii=False, indent=2),
        reference_note=reference_note,
    )


def _extract_text_from_pdfs(pdfs_b64: list[str]) -> str:
    """Extrait le texte brut des PDFs encodés en base64 (fallback modèles non-vision)."""
    import pypdf

    texts = []
    for i, pdf_b64 in enumerate(pdfs_b64, 1):
        try:
            pdf_bytes = base64.b64decode(pdf_b64)
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            pages_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if pages_text.strip():
                texts.append(f"--- Document de référence {i} ---\n{pages_text.strip()}")
        except Exception:
            pass
    return "\n\n".join(texts)


async def generate_project_content(project_data: dict, reference_pdfs: list[str] | None = None) -> dict:
    """
    Génère le contenu complet du projet via LiteLLM.
    Si des PDFs de référence sont fournis, ils sont envoyés directement au modèle.
    En cas d'échec (modèle non-vision), le texte est extrait et réinjecté dans le prompt.

    Les capacités du modèle (PDF natif, max_tokens) sont relues à chaque appel pour
    permettre le hot-swap de `LLM_MODEL` sans redémarrage.
    """
    supports_native_pdf = llm_client.supports_native_pdf()
    max_tokens = _compute_max_tokens(supports_native_pdf)
    user_prompt = _build_user_prompt(project_data, bool(reference_pdfs))

    # Construction des messages
    # Les blocs "document" natifs ne sont supportés que par Anthropic/Claude
    if reference_pdfs and supports_native_pdf:
        logger.debug("Mode PDF natif (Claude) — %d document(s)", len(reference_pdfs))
        pdf_blocks: list = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
            }
            for pdf_b64 in reference_pdfs
        ]
        pdf_blocks.append({"type": "text", "text": user_prompt})
        messages = [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": pdf_blocks},
        ]
    elif reference_pdfs:
        # Modèle non-Claude : extraction directe sans aller-retour inutile
        logger.debug("Mode extraction texte (non-Claude) — %d document(s)", len(reference_pdfs))
        extracted = _extract_text_from_pdfs(reference_pdfs)
        if extracted:
            extracted_truncated = extracted[:_MAX_EXTRACTED_CHARS]
            if len(extracted) > _MAX_EXTRACTED_CHARS:
                logger.info("Texte extrait tronqué à %d/%d caractères", _MAX_EXTRACTED_CHARS, len(extracted))
            else:
                logger.info("Texte extrait — %d caractères", len(extracted))
            user_prompt = user_prompt + f"\n\nDocuments de référence (texte extrait) :\n{extracted_truncated}"
        else:
            logger.warning("Aucun texte extrait des PDFs — génération sans documents")
        messages = [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
    else:
        messages = [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": user_prompt},
        ]

    try:
        raw = await llm_client.call_llm(messages, max_tokens=max_tokens)
    except Exception as e:
        # Fallback uniquement pour Claude (si le modèle refuse les document blocks)
        if reference_pdfs and supports_native_pdf:
            logger.warning("Échec PDF natif Claude (%s) — bascule sur extraction texte", type(e).__name__)
            extracted = _extract_text_from_pdfs(reference_pdfs)
            fallback_prompt = user_prompt
            if extracted:
                extracted_truncated = extracted[:_MAX_EXTRACTED_CHARS]
                logger.info("Texte extrait (fallback) — %d caractères", len(extracted_truncated))
                fallback_prompt = user_prompt + f"\n\nDocuments de référence (texte extrait) :\n{extracted_truncated}"
            fallback_messages = [
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": fallback_prompt},
            ]
            raw = await llm_client.call_llm(fallback_messages, max_tokens=max_tokens)
        else:
            logger.exception("Erreur génération — pas de fallback possible")
            raise

    result = llm_client.parse_json_response(raw)
    logger.debug("JSON parsé avec succès — %d clés de premier niveau", len(result))

    # Validation Pydantic : top-level strict, nested permissif. Évite les sections
    # silencieusement vides côté docx_service quand le modèle a oublié des clés.
    from schemas.generated import GeneratedContent
    validated = GeneratedContent.model_validate(result)
    logger.info(
        "Sortie LLM validée — %d parties_prenantes, %d activités, %d risques",
        len(validated.parties_prenantes), len(validated.activites_detaillees), len(validated.risques),
    )
    return validated.model_dump()
