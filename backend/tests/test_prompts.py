"""Tests du registry de prompts externalisés."""
import pytest

from services import prompts


def test_loads_known_prompts():
    for name in (
        "system_generate", "user_generate", "reference_note", "prefill",
        "mode_montage", "mode_financement",
    ):
        content = prompts.load(name)
        assert content, f"{name} ne doit pas être vide"
        assert isinstance(content, str)


def test_user_generate_has_format_placeholders():
    """Le template user_generate doit contenir les placeholders attendus."""
    content = prompts.load("user_generate")
    assert "{project_data_json}" in content
    assert "{reference_note}" in content
    assert "{mode_note}" in content


def test_user_generate_renders_with_real_payload():
    """Vérifie que les `{{` JSON ne cassent pas str.format."""
    template = prompts.load("user_generate")
    rendered = template.format(
        project_data_json='{"nom": "Test"}',
        reference_note="",
        mode_note="",
    )
    assert '"nom": "Test"' in rendered
    assert '"introduction":' in rendered  # les {{ doivent devenir {
    assert "{{" not in rendered  # tous les escapes ont été résolus


def test_load_caches_result():
    """lru_cache : deux appels successifs renvoient le MÊME objet str."""
    a = prompts.load("system_generate")
    b = prompts.load("system_generate")
    assert a is b


def test_load_missing_prompt_raises():
    with pytest.raises(FileNotFoundError):
        prompts.load("__inexistant__")
