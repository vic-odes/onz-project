"""Tests de la note conceptuelle (schéma + rendu docx + prompts)."""
import io
import zipfile

from schemas.note_conceptuelle import NoteConceptuelle
from services import docx_service, prompts


def _full() -> dict:
    return {
        "titre": "Accès à l'eau potable à Mopti",
        "resume_executif": "Un projet pour réhabiliter 20 forages.",
        "contexte": "Zone rurale, forages en panne.",
        "justification": "Aligné avec les priorités eau de l'AFD.",
        "objectif_global": "Améliorer l'accès à l'eau.",
        "objectifs_specifiques": ["Réhabiliter 20 forages", "Former les comités"],
        "resultats_attendus": ["20 forages fonctionnels"],
        "activites_principales": ["Diagnostic", "Travaux", "Formation"],
        "beneficiaires": "25 000 personnes",
        "budget_synthese": "1 M USD, dont 80 % AFD.",
        "partenaires": ["Commune", "ONG locale"],
        "durabilite": "Comités de gestion autonomes.",
        "conclusion": "Nous sollicitons le soutien de l'AFD.",
    }


def test_schema_defaults_on_empty():
    n = NoteConceptuelle.model_validate({})
    assert n.titre == ""
    assert n.objectifs_specifiques == []


def test_schema_extra_ignored():
    n = NoteConceptuelle.model_validate({"titre": "X", "hallucine": 1})
    assert n.titre == "X"
    assert not hasattr(n, "hallucine")


def test_docx_renders_full_note():
    data = docx_service.create_note_conceptuelle_document({"nom": "P", "bailleur": "AFD"}, _full())
    assert data[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    assert "NOTE CONCEPTUELLE" in xml
    assert "Résumé exécutif" in xml
    assert "Durabilité" in xml
    assert "Réhabiliter 20 forages" in xml


def test_docx_renders_minimal_note():
    """Une note quasi vide ne doit pas crasher le rendu."""
    data = docx_service.create_note_conceptuelle_document({"nom": "P"}, {"titre": "Titre seul"})
    assert data[:2] == b"PK"


def test_note_prompts_load_and_format():
    system = prompts.load("system_note_conceptuelle")
    assert "note" in system.lower()
    user = prompts.load("user_note_conceptuelle").format(project_data_json='{"nom": "X"}')
    assert "resume_executif" in user
    assert "conclusion" in user
