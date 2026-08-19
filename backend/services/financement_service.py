"""Recherche de financements compatibles avec un projet déjà monté.

Réutilise le pattern LLM → JSON → validation Pydantic déjà en place dans
`ai_service.py`/`routers/documents.py` : un appel `llm_client.call_llm`, puis
`parse_json_response` + validation avec `schemas/financement.ResultatsFinancement`.

La recherche web côté serveur (`web_search=True`) n'est activée que si le modèle
configuré la supporte (`llm_client.supports_web_search`) — sinon le modèle répond
à partir de ses seules connaissances, et le prompt lui impose de marquer chaque
opportunité `fiabilite="information_non_disponible"` plutôt que d'inventer des
dates ou des montants.
"""

import json
import logging
from datetime import datetime

from services import llm_client, prompts
from schemas.financement import ResultatsFinancement

logger = logging.getLogger(__name__)

_FINANCEMENT_MAX_TOKENS = 6000
_FINANCEMENT_TEMPERATURE = 0.2

_RECHERCHE_LIVE_NOTE = (
    "Un outil de recherche web est disponible pour cette requête : utilise-le pour "
    "trouver des opportunités réelles et actuelles, et cite leurs sources officielles."
)
_RECHERCHE_HORS_LIGNE_NOTE = (
    "Aucun outil de recherche web n'est disponible pour cette requête. Base-toi sur tes "
    "connaissances générales des bailleurs et programmes de développement international, "
    "et marque bien fiabilite=\"information_non_disponible\" sur chaque opportunité — "
    "n'invente aucune date limite ni aucun montant précis."
)


def _project_profile(project_data: dict) -> dict:
    """Sous-ensemble des champs du projet pertinent pour le matching bailleur.

    Champs volontairement limités à ceux réellement persistés sur `Project` —
    pas de champs (type de porteur, partenaire local...) qui n'existent pas en base.
    """
    return {
        "nom": project_data.get("nom", ""),
        "pays": project_data.get("pays", ""),
        "secteur": project_data.get("secteur", ""),
        "probleme_principal": project_data.get("probleme_principal", ""),
        "objectif_global": project_data.get("objectif_global", ""),
        "budget_total": project_data.get("budget_total"),
        "duree_mois": project_data.get("duree_mois"),
    }


async def rechercher_financements(project_data: dict) -> tuple[ResultatsFinancement, bool]:
    """Lance la recherche de financements pour un projet.

    Retourne `(resultats, recherche_live)` où `recherche_live` indique si la
    recherche web côté serveur était activée pour cet appel.
    """
    recherche_live = llm_client.supports_web_search()
    date_du_jour = datetime.now().strftime("%d/%m/%Y")

    user_prompt = prompts.load("user_financement").format(
        date_du_jour=date_du_jour,
        project_data_json=json.dumps(_project_profile(project_data), ensure_ascii=False, indent=2),
        recherche_note=_RECHERCHE_LIVE_NOTE if recherche_live else _RECHERCHE_HORS_LIGNE_NOTE,
    )
    messages = [
        {"role": "system", "content": prompts.load("system_financement")},
        {"role": "user", "content": user_prompt},
    ]

    logger.info(
        "Recherche de financement démarrée — projet=%r pays=%r secteur=%r recherche_live=%s",
        project_data.get("nom"), project_data.get("pays"), project_data.get("secteur"), recherche_live,
    )

    raw = await llm_client.call_llm(
        messages,
        max_tokens=_FINANCEMENT_MAX_TOKENS,
        temperature=_FINANCEMENT_TEMPERATURE,
        web_search=recherche_live,
    )
    result = llm_client.parse_json_response(raw)
    resultats = ResultatsFinancement.model_validate(result)

    logger.info(
        "Recherche de financement terminée — %d opportunité(s) identifiée(s)",
        len(resultats.opportunites),
    )
    return resultats, recherche_live
