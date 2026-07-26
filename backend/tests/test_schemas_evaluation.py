"""Tests du schéma `Evaluation` (lot B : analyse bailleur + notation)."""
from schemas.evaluation import Evaluation
from services import prompts


def test_empty_payload_uses_defaults():
    """Volets optionnels : un payload vide ne lève pas et applique les defaults."""
    out = Evaluation.model_validate({})
    assert out.analyse_bailleur.score_compatibilite == 0
    assert out.analyse_bailleur.priorites == []
    assert out.notation.score_total_sur_100 == 0.0
    assert out.notation.criteres == []


def test_full_payload():
    payload = {
        "analyse_bailleur": {
            "nom": "AFD",
            "priorites": ["Climat", "Genre"],
            "criteres_eligibilite": ["ONG enregistrée"],
            "montant_max_finançable": "jusqu'à 2 M€",
            "taux_cofinancement": "15-20 %",
            "score_compatibilite": 82,
            "risques_rejet": ["Budget peu détaillé"],
        },
        "notation": {
            "criteres": [
                {"critere": "Pertinence", "note_sur_20": 17, "commentaire": "Fort alignement"},
                {"critere": "Durabilité", "note_sur_20": 12, "commentaire": "À renforcer"},
            ],
            "score_total_sur_100": 74,
            "points_forts": ["Ancrage local"],
            "axes_amelioration": ["Détailler le budget"],
            "recommandation": "Renforcer avant soumission.",
        },
    }
    out = Evaluation.model_validate(payload)
    assert out.analyse_bailleur.nom == "AFD"
    assert out.analyse_bailleur.score_compatibilite == 82
    assert out.notation.criteres[0].note_sur_20 == 17.0
    assert out.notation.score_total_sur_100 == 74.0


def test_score_coerces_numeric_string():
    """Le LLM peut renvoyer '82' (string) — Pydantic coerce vers int."""
    out = Evaluation.model_validate({"analyse_bailleur": {"score_compatibilite": "82"}})
    assert out.analyse_bailleur.score_compatibilite == 82


def test_extra_keys_ignored():
    out = Evaluation.model_validate({"analyse_bailleur": {"nom": "UE", "hallucine": 1}, "extra": True})
    assert out.analyse_bailleur.nom == "UE"
    assert not hasattr(out.analyse_bailleur, "hallucine")


def test_nested_partial_critere():
    out = Evaluation.model_validate({"notation": {"criteres": [{"critere": "Impact"}]}})
    assert out.notation.criteres[0].critere == "Impact"
    assert out.notation.criteres[0].note_sur_20 == 0.0  # default


def test_evaluation_prompts_load_and_format():
    """Les prompts existent et le template user se formate sans KeyError."""
    system = prompts.load("system_evaluation")
    assert "évaluateur" in system.lower()
    user = prompts.load("user_evaluation").format(project_data_json='{"nom": "X"}')
    assert "analyse_bailleur" in user
    assert "score_compatibilite" in user
