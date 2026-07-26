"""Tests du mode de dossier (montage vs demande de financement)."""
import pytest
from pydantic import ValidationError

from schemas.project import ProjectCreate
from services.ai_service import _build_user_prompt


def _base() -> dict:
    return {
        "nom": "P", "pays": "Mali", "secteur": "Eau", "bailleur": "AFD",
        "probleme_principal": "x", "objectif_global": "y",
    }


def test_type_dossier_defaults_to_montage():
    p = ProjectCreate(**_base())
    assert p.type_dossier == "montage"


def test_type_dossier_accepts_financement():
    p = ProjectCreate(**_base(), type_dossier="financement")
    assert p.type_dossier == "financement"


def test_type_dossier_rejects_invalid():
    with pytest.raises(ValidationError):
        ProjectCreate(**_base(), type_dossier="autre_chose")


def test_prompt_injects_montage_note_by_default():
    prompt = _build_user_prompt({"nom": "P", "type_dossier": "montage"}, has_references=False)
    assert "planification interne" in prompt.lower()
    assert "demande de subvention" not in prompt.lower()


def test_prompt_injects_financement_note():
    prompt = _build_user_prompt({"nom": "P", "type_dossier": "financement"}, has_references=False)
    assert "demande de subvention" in prompt.lower()
    # Le template et ses clés JSON restent présents (même schéma dans les deux modes)
    assert "analyse_cout_benefice" in prompt


def test_prompt_missing_type_dossier_falls_back_to_montage():
    prompt = _build_user_prompt({"nom": "P"}, has_references=False)
    assert "planification interne" in prompt.lower()
