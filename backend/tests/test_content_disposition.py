"""Régression : l'en-tête Content-Disposition doit rester ASCII/latin-1.

Bug historique : `str.isalnum()` étant Unicode-aware, un nom accentué
(« Café », « Éducation ») ou non-latin passait tel quel dans l'en-tête HTTP, qui
ne supporte pas l'UTF-8 brut → réponse cassée (UnicodeError côté serveur/proxy).
Le helper produit désormais un repli ASCII + un `filename*=UTF-8''` (RFC 5987).
"""
import pytest

from http_utils import content_disposition_attachment


@pytest.mark.parametrize(
    "filename",
    [
        "Accès à l'eau potable - Région de Mopti_ONZ.docx",
        "Éducation & Santé_budget_ONZ.xlsx",
        "مشروع المياه.xlsx",  # arabe
        "Проект.docx",         # cyrillique
        "🌍 Climat.xlsx",       # emoji hors latin-1
        "",                     # vide -> fallback "fichier"
    ],
)
def test_header_is_latin1_encodable(filename):
    """Un en-tête HTTP doit être encodable en latin-1 : c'est la vraie contrainte
    qui cassait avec un nom accentué/non-latin."""
    header = content_disposition_attachment(filename)
    header.encode("latin-1")  # ne doit pas lever


def test_header_has_both_forms():
    header = content_disposition_attachment("Accès Café_ONZ.docx")
    assert header.startswith("attachment; ")
    assert 'filename="' in header          # repli ASCII
    assert "filename*=UTF-8''" in header    # version encodée RFC 5987
    ascii_part = header.split('filename="', 1)[1].split('"', 1)[0]
    assert ascii_part.isascii()
    assert ascii_part.endswith("_ONZ.docx")


def test_empty_name_falls_back():
    header = content_disposition_attachment("   ")
    assert 'filename="fichier"' in header
