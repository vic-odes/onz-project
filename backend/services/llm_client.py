"""Client LLM unifié — point d'entrée unique pour tout appel LiteLLM.

Centralise :
- l'initialisation des flags `litellm`
- la lecture du modèle et des paramètres Azure depuis `.env`
- l'appel `acompletion` avec gestion uniforme des erreurs (réponse tronquée, vide)
- le nettoyage des balises markdown ```json ... ``` dans la réponse
- le parsing JSON

Tout nouvel appel LLM doit passer par ce module. Cela évite la duplication entre
`services/ai_service.py` et `routers/documents.py`.
"""

import json
import logging
import os
from typing import AsyncIterator, Optional

import litellm
from dotenv import load_dotenv

# Initialisation globale — une seule fois par process
load_dotenv(override=True)
litellm.drop_params = True
litellm.suppress_debug_info = True
litellm.set_verbose = False

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


def get_model() -> str:
    """Modèle courant. Lu à chaque appel pour permettre les overrides à chaud (tests)."""
    return os.getenv("LLM_MODEL", DEFAULT_MODEL)


def supports_native_pdf(model: Optional[str] = None) -> bool:
    """Les blocs `document` natifs ne sont supportés que par les modèles Anthropic/Claude."""
    return "claude" in (model or get_model()).lower()


def azure_extras() -> dict:
    """Kwargs Azure à passer à `litellm.acompletion`, vides si non configurés."""
    extras = {}
    if (k := os.getenv("AZURE_API_KEY")):
        extras["api_key"] = k
    if (b := os.getenv("AZURE_API_BASE")):
        extras["api_base"] = b
    if (v := os.getenv("AZURE_API_VERSION")):
        extras["api_version"] = v
    return extras


def _strip_markdown_fences(content: str) -> str:
    """Retire les balises ```json ... ``` d'une réponse LLM."""
    return (
        content.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )


async def call_llm(
    messages: list,
    *,
    max_tokens: int,
    temperature: float = 0.3,
    model: Optional[str] = None,
    extra: Optional[dict] = None,
) -> str:
    """Appelle le LLM via LiteLLM et retourne la réponse texte nettoyée.

    Lève :
    - `ValueError` si la réponse est vide, tronquée (`finish_reason="length"`),
      ou ne contient plus rien après nettoyage des balises markdown.
    - Toute exception remontée par `litellm.acompletion` (réseau, auth, etc.).
    """
    used_model = model or get_model()
    used_extra = extra if extra is not None else azure_extras()

    logger.debug(
        "LLM call — model=%s max_tokens=%d temperature=%s messages=%d extra_keys=%s",
        used_model, max_tokens, temperature, len(messages), list(used_extra.keys()),
    )
    response = await litellm.acompletion(
        model=used_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        **used_extra,
    )
    finish_reason = response.choices[0].finish_reason
    content = response.choices[0].message.content
    logger.debug(
        "LLM response — finish_reason=%s content_len=%s",
        finish_reason, len(content) if content else "None",
    )

    if not content:
        if finish_reason == "length":
            logger.error(
                "Limite de tokens atteinte (max_tokens=%d) — réponse tronquée/vide.",
                max_tokens,
            )
            raise ValueError(
                f"Le modèle a atteint la limite de tokens ({max_tokens}). "
                "Réduisez les documents joints ou augmentez LLM_MAX_TOKENS."
            )
        logger.error("Le modèle a retourné un contenu vide (finish_reason=%s)", finish_reason)
        raise ValueError("Le modèle a retourné une réponse vide.")

    cleaned = _strip_markdown_fences(content)
    if not cleaned:
        logger.error("Contenu vide après nettoyage des balises markdown. Brut: %r", content[:200])
        raise ValueError("Le modèle a retourné une réponse vide après nettoyage.")
    return cleaned


async def stream_llm(
    messages: list,
    *,
    max_tokens: int,
    temperature: float = 0.3,
    model: Optional[str] = None,
    extra: Optional[dict] = None,
) -> AsyncIterator[str]:
    """Variante streaming de `call_llm` : yield chaque delta texte au fur et à mesure.

    L'appelant peut utiliser ces deltas pour afficher un compteur de tokens / une
    progression côté UI, puis reconstruire la réponse complète en concaténant.

    Lève les mêmes exceptions que `call_llm` (réseau, auth) pendant la phase initiale.
    En fin de stream, si `finish_reason == "length"`, lève `ValueError` avant de
    retourner — l'appelant n'a alors PAS de JSON exploitable.
    """
    used_model = model or get_model()
    used_extra = extra if extra is not None else azure_extras()

    logger.debug(
        "LLM stream — model=%s max_tokens=%d temperature=%s messages=%d extra_keys=%s",
        used_model, max_tokens, temperature, len(messages), list(used_extra.keys()),
    )
    response = await litellm.acompletion(
        model=used_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        **used_extra,
    )

    finish_reason: Optional[str] = None
    total_chars = 0
    async for chunk in response:
        choice = chunk.choices[0] if chunk.choices else None
        if choice is None:
            continue
        if (delta := getattr(choice, "delta", None)) and (text := getattr(delta, "content", None)):
            total_chars += len(text)
            yield text
        if (reason := getattr(choice, "finish_reason", None)):
            finish_reason = reason

    logger.debug("LLM stream terminé — finish_reason=%s chars=%d", finish_reason, total_chars)

    if finish_reason == "length":
        logger.error("Stream tronqué (max_tokens=%d, chars=%d)", max_tokens, total_chars)
        raise ValueError(
            f"Le modèle a atteint la limite de tokens ({max_tokens}). "
            "Réduisez les documents joints ou augmentez LLM_MAX_TOKENS."
        )
    if total_chars == 0:
        logger.error("Stream vide (finish_reason=%s)", finish_reason)
        raise ValueError("Le modèle a retourné une réponse vide.")


def strip_markdown_fences(content: str) -> str:
    """Public : retire les balises ```json ... ``` (utilisé après concaténation d'un stream)."""
    return _strip_markdown_fences(content)


def parse_json_response(raw: str) -> dict:
    """Parse une réponse LLM JSON. Lève `json.JSONDecodeError` si invalide."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("JSON invalide retourné. Début du contenu brut: %r", raw[:500])
        raise


__all__ = [
    "get_model",
    "supports_native_pdf",
    "azure_extras",
    "call_llm",
    "stream_llm",
    "strip_markdown_fences",
    "parse_json_response",
]
