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
from typing import Optional

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
        # Mode JSON natif : garantit une sortie JSON valide côté OpenAI/Azure.
        # litellm.drop_params retire automatiquement ce paramètre pour les
        # modèles qui ne le supportent pas (ex. certains modèles Anthropic).
        response_format={"type": "json_object"},
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


def strip_markdown_fences(content: str) -> str:
    """Public : retire les balises ```json ... ``` (utilisé après concaténation d'un stream)."""
    return _strip_markdown_fences(content)


def parse_json_response(raw: str) -> dict:
    """Parse une réponse LLM JSON.

    Beaucoup de modèles produisent un JSON *presque* valide sur les longues
    sorties (guillemet non échappé dans une valeur, virgule finale, caractère de
    contrôle…). On tente donc une réparation automatique avant d'abandonner ;
    ça évite un échec 502 pour une simple faute de syntaxe récupérable.

    Lève `json.JSONDecodeError` uniquement si même la réparation ne donne pas
    un objet JSON exploitable.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("JSON invalide (%s) — tentative de réparation automatique", exc)
        try:
            from json_repair import repair_json
            repaired = repair_json(raw, return_objects=True)
        except Exception:  # pragma: no cover - la lib ne devrait pas lever
            repaired = None
        if isinstance(repaired, dict) and repaired:
            logger.info("JSON réparé avec succès — %d clés de premier niveau", len(repaired))
            return repaired
        logger.error(
            "JSON irréparable. Début du contenu brut: %r", raw[:500]
        )
        raise exc


__all__ = [
    "get_model",
    "supports_native_pdf",
    "azure_extras",
    "call_llm",
    "strip_markdown_fences",
    "parse_json_response",
]
