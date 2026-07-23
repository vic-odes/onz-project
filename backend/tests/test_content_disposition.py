"""Régression : l'en-tête Content-Disposition du .docx doit rester ASCII/latin-1.

Bug historique : `str.isalnum()` étant Unicode-aware, un nom de projet accentué
(« Café », « Éducation ») ou non-latin passait tel quel dans l'en-tête HTTP, qui
ne supporte pas l'UTF-8 brut → réponse cassée (UnicodeError côté serveur/proxy).
Le helper produit désormais un repli ASCII + un `filename*=UTF-8''` (RFC 5987).
"""
import pytest

from routers.generate import _content_disposition


@pytest.mark.parametrize(
    "nom",
    [
        "Accès à l'eau potable - Région de Mopti",
        "Éducation & Santé",
        "مشروع المياه",  # arabe
        "Проект",         # cyrillique
        "🌍 Climat",       # emoji hors latin-1
        "",                # vide -> fallback "Projet"
    ],
)
def test_header_is_latin1_encodable(nom):
    """Un en-tête HTTP doit être encodable en latin-1 : c'est la vraie contrainte
    qui cassait avec un nom accentué/non-latin."""
    header = _content_disposition(nom)
    # Ne doit pas lever — c'est ce qui échouait avant le correctif.
    header.encode("latin-1")


def test_header_has_both_forms():
    header = _content_disposition("Accès Café")
    assert header.startswith("attachment; ")
    assert 'filename="' in header          # repli ASCII
    assert "filename*=UTF-8''" in header    # version encodée RFC 5987
    # Le repli ASCII ne contient aucun caractère non-ASCII
    ascii_part = header.split('filename="', 1)[1].split('"', 1)[0]
    assert ascii_part.isascii()
    assert ascii_part.endswith("_ONZ.docx")


def test_empty_name_falls_back_to_projet():
    header = _content_disposition("   ")
    assert 'filename="Projet_ONZ.docx"' in header
