"""Tests du schéma `GeneratedContent` — sortie LLM validée.

Stratégie testée :
- Top-level strict : clé manquante → ValidationError.
- Nested permissif : sous-clés absentes → defaults.
- extra="ignore" : clés hallucinées tolérées.
"""
import pytest
from pydantic import ValidationError

from schemas.generated import GeneratedContent


def _minimal_payload() -> dict:
    """Payload minimal valide — toutes les clés top-level requises."""
    return {
        "introduction": "intro",
        "cadre_logique": {},
        "parties_prenantes": [],
        "activites_detaillees": [],
        "chronogramme": [],
        "budget": {},
        "analyse_cout_benefice": {},
        "risques": [],
        "communication": "comm",
    }


def test_minimal_payload_validates():
    out = GeneratedContent.model_validate(_minimal_payload())
    assert out.introduction == "intro"
    # Defaults : note_conceptuelle / resume_executif optionnels
    assert out.note_conceptuelle == ""
    assert out.resume_executif == ""


def test_missing_top_level_key_fails():
    payload = _minimal_payload()
    del payload["cadre_logique"]
    with pytest.raises(ValidationError) as exc_info:
        GeneratedContent.model_validate(payload)
    assert "cadre_logique" in str(exc_info.value)


def test_nested_partial_partie_prenante_ok():
    """Un PartiePrenante avec uniquement `nom` doit passer (nested permissif)."""
    payload = _minimal_payload()
    payload["parties_prenantes"] = [{"nom": "Ministère"}]
    out = GeneratedContent.model_validate(payload)
    assert out.parties_prenantes[0].nom == "Ministère"
    assert out.parties_prenantes[0].influence == ""  # default


def test_extra_keys_ignored():
    """Le LLM peut halluciner des clés supplémentaires — elles doivent être tolérées."""
    payload = _minimal_payload()
    payload["champ_hallucine"] = "valeur"
    payload["budget"]["champ_inattendu"] = 42
    out = GeneratedContent.model_validate(payload)
    assert not hasattr(out, "champ_hallucine")
    assert not hasattr(out.budget, "champ_inattendu")


def test_budget_lignes_partial():
    payload = _minimal_payload()
    payload["budget"] = {"lignes": [{"categorie": "RH"}], "total_usd": 1000}
    out = GeneratedContent.model_validate(payload)
    assert out.budget.lignes[0].categorie == "RH"
    assert out.budget.lignes[0].montant_usd == 0.0  # default
    assert out.budget.total_usd == 1000.0


def test_optional_fields_default_empty_string():
    payload = _minimal_payload()
    out = GeneratedContent.model_validate(payload)
    assert out.note_conceptuelle == ""
    assert out.resume_executif == ""


def test_model_dump_round_trip():
    payload = _minimal_payload()
    out = GeneratedContent.model_validate(payload)
    dumped = out.model_dump()
    # docx_service consomme le dict — toutes les clés top-level doivent y être
    for key in (
        "introduction", "cadre_logique", "parties_prenantes",
        "activites_detaillees", "chronogramme", "budget",
        "analyse_cout_benefice", "risques", "communication",
    ):
        assert key in dumped
