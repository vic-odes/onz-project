"""Tests de `services/financement_service.py` — LLM mocké, pas d'appel réel."""
from __future__ import annotations

import pytest

from services import financement_service, llm_client

_FAKE_RAW = """{
  "resume": "1 opportunité identifiée.",
  "opportunites": [
    {"bailleur": "AFD", "categorie": "compatible", "score_compatibilite": 70}
  ]
}"""

_PROJECT = {
    "nom": "Adduction eau Makénéné",
    "pays": "Cameroun",
    "secteur": "Eau & Assainissement",
    "probleme_principal": "Accès limité à l'eau potable",
    "objectif_global": "Améliorer l'accès à l'eau potable",
    "budget_total": 1200000,
    "duree_mois": 36,
    "bailleur": "Recherche automatique de bailleur",  # ne doit pas apparaître dans le profil envoyé
}


@pytest.mark.asyncio
async def test_rechercher_financements_happy_path(monkeypatch):
    captured = {}

    async def _fake_call_llm(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return _FAKE_RAW

    monkeypatch.setattr(llm_client, "supports_web_search", lambda: True)
    monkeypatch.setattr(financement_service.llm_client, "call_llm", _fake_call_llm)

    resultats, recherche_live = await financement_service.rechercher_financements(_PROJECT)

    assert recherche_live is True
    assert len(resultats.opportunites) == 1
    assert resultats.opportunites[0].bailleur == "AFD"
    assert captured["kwargs"]["web_search"] is True
    # Le profil envoyé au LLM ne doit pas contenir le champ bailleur (recherche large,
    # pas ciblée sur le bailleur déjà choisi le cas échéant).
    user_content = captured["messages"][1]["content"]
    assert "Recherche automatique de bailleur" not in user_content
    assert "Cameroun" in user_content


@pytest.mark.asyncio
async def test_rechercher_financements_without_web_search(monkeypatch):
    captured = {}

    async def _fake_call_llm(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return _FAKE_RAW

    monkeypatch.setattr(llm_client, "supports_web_search", lambda: False)
    monkeypatch.setattr(financement_service.llm_client, "call_llm", _fake_call_llm)

    _, recherche_live = await financement_service.rechercher_financements(_PROJECT)

    assert recherche_live is False
    assert captured["kwargs"]["web_search"] is False
    user_content = captured["messages"][1]["content"]
    assert "information_non_disponible" in user_content
