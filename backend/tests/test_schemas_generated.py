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
        # Sections ajoutées (lot A) — présentes même si le LLM les omet
        "theorie_changement", "arbre_problemes", "plan_financement",
        "perennisation",
    ):
        assert key in dumped


# --------------------------------------------------------------------------- #
# Sections ajoutées (lot A) : optionnelles au top-level, nested permissif.
# --------------------------------------------------------------------------- #


def test_new_top_level_sections_are_optional():
    """L'absence de theorie_changement / arbre_problemes / plan_financement /
    perennisation ne doit PAS lever ValidationError (default appliqué)."""
    out = GeneratedContent.model_validate(_minimal_payload())
    assert out.perennisation == ""
    assert out.theorie_changement.narratif == ""
    assert out.arbre_problemes.probleme_central == ""
    assert out.plan_financement.lignes == []
    assert out.plan_financement.total_usd == 0.0


def test_cadre_logique_matrice_partial():
    payload = _minimal_payload()
    payload["cadre_logique"] = {"matrice": [{"niveau": "Objectif global"}]}
    out = GeneratedContent.model_validate(payload)
    assert out.cadre_logique.matrice[0].niveau == "Objectif global"
    assert out.cadre_logique.matrice[0].indicateurs == ""  # default


def test_budget_ventilations():
    payload = _minimal_payload()
    payload["budget"] = {
        "par_annee": [{"annee": "Année 1", "montant_usd": 500}],
        "par_partenaire": [{"partenaire": "ONG", "montant_usd": 800}],
    }
    out = GeneratedContent.model_validate(payload)
    assert out.budget.par_annee[0].annee == "Année 1"
    assert out.budget.par_annee[0].montant_usd == 500.0
    assert out.budget.par_partenaire[0].partenaire == "ONG"


def test_plan_financement_lignes():
    payload = _minimal_payload()
    payload["plan_financement"] = {
        "lignes": [{"financeur": "UE", "montant_usd": 800, "pourcentage": 80}],
        "total_usd": 1000,
    }
    out = GeneratedContent.model_validate(payload)
    assert out.plan_financement.lignes[0].financeur == "UE"
    assert out.plan_financement.lignes[0].type == ""  # default
    assert out.plan_financement.total_usd == 1000.0


def test_analyse_cout_benefice_new_fields():
    payload = _minimal_payload()
    payload["analyse_cout_benefice"] = {"van": 12000, "tri": 14.5, "delai_retour_annees": 3.2}
    out = GeneratedContent.model_validate(payload)
    assert out.analyse_cout_benefice.van == 12000.0
    assert out.analyse_cout_benefice.tri == 14.5
    assert out.analyse_cout_benefice.delai_retour_annees == 3.2
    assert out.analyse_cout_benefice.benefices_annee1_usd == 0.0  # default


def test_risque_scoring_fields():
    payload = _minimal_payload()
    payload["risques"] = [{"risque": "Retard", "categorie": "Opérationnel", "niveau": "Élevé"}]
    out = GeneratedContent.model_validate(payload)
    assert out.risques[0].categorie == "Opérationnel"
    assert out.risques[0].niveau == "Élevé"
    assert out.risques[0].mitigation == ""  # default
