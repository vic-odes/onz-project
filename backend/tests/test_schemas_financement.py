"""Tests du schéma `ResultatsFinancement` et des prompts de recherche de financement."""
from schemas.financement import OpportuniteFinancement, ResultatsFinancement
from services import prompts


def test_empty_payload_uses_defaults():
    out = ResultatsFinancement.model_validate({})
    assert out.resume == ""
    assert out.opportunites == []


def test_full_opportunite_payload():
    payload = {
        "resume": "1 opportunité très compatible.",
        "opportunites": [
            {
                "bailleur": "AFD",
                "programme": "Programme Eau Afrique",
                "categorie": "tres_compatible",
                "score_compatibilite": 91,
                "montant_min": 100000,
                "montant_max": 600000,
                "devise": "EUR",
                "date_limite": "30/11/2026",
                "depot_permanent": False,
                "raisons_compatibilite": ["Cameroun éligible"],
                "points_vigilance": ["Cofinancement nécessaire"],
                "source_officielle": "https://www.afd.fr",
                "lien_candidature": "https://www.afd.fr/appel",
                "fiabilite": "verifie",
                "date_verification": "19/08/2026",
            }
        ],
    }
    out = ResultatsFinancement.model_validate(payload)
    assert len(out.opportunites) == 1
    opp = out.opportunites[0]
    assert opp.bailleur == "AFD"
    assert opp.score_compatibilite == 91
    assert opp.categorie == "tres_compatible"
    assert opp.fiabilite == "verifie"


def test_nested_partial_opportunite_gets_defaults():
    out = ResultatsFinancement.model_validate({"opportunites": [{"bailleur": "UE"}]})
    opp = out.opportunites[0]
    assert opp.bailleur == "UE"
    assert opp.categorie == "a_etudier"  # default
    assert opp.fiabilite == "information_non_disponible"  # default
    assert opp.score_compatibilite == 0
    assert opp.raisons_compatibilite == []


def test_extra_keys_ignored():
    out = ResultatsFinancement.model_validate({"opportunites": [{"bailleur": "PNUD", "hallucine": 1}]})
    assert out.opportunites[0].bailleur == "PNUD"
    assert not hasattr(out.opportunites[0], "hallucine")


def test_invalid_categorie_raises():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        OpportuniteFinancement.model_validate({"categorie": "pas_une_categorie_valide"})


def test_score_coerces_numeric_string():
    out = OpportuniteFinancement.model_validate({"score_compatibilite": "91"})
    assert out.score_compatibilite == 91


def test_financement_prompts_load_and_format():
    system = prompts.load("system_financement")
    assert "financement" in system.lower()
    assert "ne jamais inventer" in system.lower() or "jamais" in system.lower()

    user = prompts.load("user_financement").format(
        date_du_jour="19/08/2026",
        project_data_json='{"nom": "X"}',
        recherche_note="Note.",
    )
    assert "opportunites" in user
    assert "19/08/2026" in user
