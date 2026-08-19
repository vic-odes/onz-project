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


@pytest.mark.parametrize("model,expected", [
    ("claude-sonnet-4-20250514", True),
    ("claude-3-5-haiku-20241022", True),
    ("gpt-4o", False),
    ("mistral-large-latest", False),
])
def test_supports_web_search(model, expected):
    assert llm_client.supports_web_search(model) is expected


def test_azure_extras_empty_for_claude_even_if_azure_vars_set(monkeypatch):
    """Des variables AZURE_API_* laissées en place (ex. ancienne config Azure
    OpenAI) ne doivent jamais s'appliquer à un modèle Claude — sinon elles
    écraseraient silencieusement ANTHROPIC_API_KEY/ANTHROPIC_API_BASE."""
    monkeypatch.setenv("AZURE_API_KEY", "azure-openai-key")
    monkeypatch.setenv("AZURE_API_BASE", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_API_VERSION", "2024-08-01-preview")
    assert llm_client.azure_extras("azure/claude-haiku-4-5") == {}
    assert llm_client.azure_extras("anthropic/claude-haiku-4-5") == {}
    assert llm_client.azure_extras("claude-haiku-4-5") == {}


def test_azure_extras_applies_for_non_claude_model(monkeypatch):
    monkeypatch.setenv("AZURE_API_KEY", "azure-openai-key")
    monkeypatch.setenv("AZURE_API_BASE", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_API_VERSION", "2024-08-01-preview")
    assert llm_client.azure_extras("azure/gpt-5.4-nano") == {
        "api_key": "azure-openai-key",
        "api_base": "https://example.openai.azure.com",
        "api_version": "2024-08-01-preview",
    }


def test_azure_extras_empty_when_nothing_set(monkeypatch):
    monkeypatch.delenv("AZURE_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_API_BASE", raising=False)
    monkeypatch.delenv("AZURE_API_VERSION", raising=False)
    assert llm_client.azure_extras("gpt-4o") == {}


@pytest.mark.asyncio
async def test_call_llm_raises_on_truncation_with_partial_content(monkeypatch):
    """Régression : une troncature (finish_reason="length") avec du contenu
    PARTIEL (le cas réel le plus fréquent — le modèle a déjà écrit une grande
    partie du JSON avant d'atteindre max_tokens) doit lever une erreur claire,
    plutôt que laisser le JSON tronqué partir vers parse_json_response()."""
    class _FakeChoice:
        finish_reason = "length"
        message = type("M", (), {"content": '{"introduction": "texte partiel...'})()

    class _FakeResponse:
        choices = [_FakeChoice()]

    async def _fake_acompletion(**kwargs):
        return _FakeResponse()

    monkeypatch.setattr(llm_client.litellm, "acompletion", _fake_acompletion)

    with pytest.raises(ValueError, match="limite de tokens"):
        await llm_client.call_llm([{"role": "user", "content": "x"}], max_tokens=16000)


@pytest.mark.asyncio
async def test_call_llm_raises_on_truncation_with_empty_content(monkeypatch):
    """Cas historique : troncature avec contenu totalement vide."""
    class _FakeChoice:
        finish_reason = "length"
        message = type("M", (), {"content": ""})()

    class _FakeResponse:
        choices = [_FakeChoice()]

    async def _fake_acompletion(**kwargs):
        return _FakeResponse()

    monkeypatch.setattr(llm_client.litellm, "acompletion", _fake_acompletion)

    with pytest.raises(ValueError, match="limite de tokens"):
        await llm_client.call_llm([{"role": "user", "content": "x"}], max_tokens=16000)


@pytest.mark.asyncio
async def test_call_llm_passes_web_search_options(monkeypatch):
    captured = {}

    class _FakeChoice:
        finish_reason = "end_turn"
        message = type("M", (), {"content": '{"ok": true}'})()

    class _FakeResponse:
        choices = [_FakeChoice()]

    async def _fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse()

    monkeypatch.setattr(llm_client.litellm, "acompletion", _fake_acompletion)

    await llm_client.call_llm(
        [{"role": "user", "content": "x"}],
        max_tokens=100,
        model="claude-sonnet-4-20250514",
        web_search=True,
    )
    assert captured.get("web_search_options") == {"search_context_size": "medium"}


@pytest.mark.asyncio
async def test_call_llm_omits_web_search_options_by_default(monkeypatch):
    captured = {}

    class _FakeChoice:
        finish_reason = "end_turn"
        message = type("M", (), {"content": '{"ok": true}'})()

    class _FakeResponse:
        choices = [_FakeChoice()]

    async def _fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse()

    monkeypatch.setattr(llm_client.litellm, "acompletion", _fake_acompletion)

    await llm_client.call_llm([{"role": "user", "content": "x"}], max_tokens=100)
    assert "web_search_options" not in captured
