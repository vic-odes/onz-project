"""Tests unitaires ciblés sur ai_service (lecture robuste de LLM_MAX_TOKENS)."""
from __future__ import annotations

import pytest

from services import ai_service


@pytest.mark.parametrize("env_val,expected", [
    (None, 16000),        # non défini → défaut
    ("32000", 32000),     # valeur valide
    (" 24000 ", 24000),   # espaces parasites tolérés
    ("0", 16000),         # <= 0 → défaut
    ("-5", 16000),        # négatif → défaut
    ("16k", 16000),       # non entier → défaut (pas de 500)
    ("", 16000),          # vide → défaut
])
def test_compute_max_tokens(monkeypatch, env_val, expected):
    if env_val is None:
        monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    else:
        monkeypatch.setenv("LLM_MAX_TOKENS", env_val)
    assert ai_service._compute_max_tokens(supports_native_pdf=False) == expected
