"""
Registry des prompts LLM externalisés dans `backend/prompts/`.

Pourquoi externaliser : faciliter le versioning, l'A/B testing et la lecture
sans toucher au code Python. Les fichiers sont en `.md` (édition agréable),
chargés une fois et mis en cache.

Format des templates : si le fichier contient `{nom}`, on utilise `str.format`
côté caller (template léger sans dépendance Jinja).
"""

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=None)
def load(name: str) -> str:
    """Charge un prompt depuis `backend/prompts/{name}.md`.

    Le résultat est mis en cache (les prompts ne changent pas en cours d'exécution).
    Pour un override à chaud, redémarrer le process — comportement volontaire,
    aligné avec les habitudes de déploiement.
    """
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt introuvable : {path}")
    return path.read_text(encoding="utf-8").strip()
