"""Tests du parseur JSON de llm_client, notamment la réparation automatique
des sorties LLM presque-valides (cause du 502 « Expecting ',' delimiter »)."""
from __future__ import annotations

import json

import pytest

from services import llm_client


def test_parse_valid_json():
    assert llm_client.parse_json_response('{"a": 1, "b": [2, 3]}') == {"a": 1, "b": [2, 3]}


def test_parse_repairs_unescaped_quote():
    # Guillemet non échappé dans une valeur → json.loads lève, la réparation récupère.
    broken = '{"introduction": "accès à l"eau potable", "budget": {"total": 1200000}}'
    with pytest.raises(json.JSONDecodeError):
        json.loads(broken)
    result = llm_client.parse_json_response(broken)
    assert result["budget"]["total"] == 1200000
    assert "introduction" in result


def test_parse_repairs_trailing_comma():
    broken = '{"risques": ["a", "b",], "communication": "ok",}'
    result = llm_client.parse_json_response(broken)
    assert result["risques"] == ["a", "b"]
    assert result["communication"] == "ok"


def test_parse_unrepairable_raises():
    # Texte qui n'est pas du JSON d'objet du tout → on remonte l'erreur d'origine.
    with pytest.raises(json.JSONDecodeError):
        llm_client.parse_json_response("ceci n'est pas du JSON")
