"""Tests du pipeline SSE de `routers/generate._generate_events`.

On mocke :
- `ai_service.stream_project_content` (générateur async) — pas d'appel LLM réel,
- `docx_service.create_word_document` — pour ne pas dépendre de python-docx,
- `database.save_project` — pour ne pas toucher à SQLite/Alembic.

Le but est de vérifier la séquence d'événements SSE émis par l'orchestrateur.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import pytest
from pydantic import ValidationError

from routers import generate as generate_router
from schemas.project import ProjectCreate


def _project() -> ProjectCreate:
    return ProjectCreate(
        nom="Projet Test",
        pays="Mali",
        secteur="Eau & Assainissement",
        bailleur="AFD",
        probleme_principal="Accès à l'eau",
        objectif_global="Améliorer l'accès",
        objectifs_specifiques=["Forer 10 puits"],
        population_cible="Ruraux",
        nombre_beneficiaires=50000,
        duree_mois=24,
        date_debut="2026-01-01",
        contraintes="",
        risques_identifies="",
        budget_total=500000,
        source_financement="AFD",
        part_couts_operationnels=30,
        generer_note_conceptuelle=False,
        inclure_resume_executif=False,
    )


def _parse_sse(blob: bytes) -> list[tuple[str, dict]]:
    """Parse un flux SSE en liste de (event_name, data_dict)."""
    events = []
    for record in blob.decode("utf-8").split("\n\n"):
        if not record.strip():
            continue
        name = None
        data = None
        for line in record.splitlines():
            if line.startswith("event: "):
                name = line[len("event: "):].strip()
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if name and data is not None:
            events.append((name, data))
    return events


async def _collect(it: AsyncIterator[bytes]) -> bytes:
    out = bytearray()
    async for chunk in it:
        out.extend(chunk)
    return bytes(out)


# ─── Mocks ──────────────────────────────────────────────────────────────────

_FAKE_GENERATED = {
    "introduction": "intro",
    "cadre_logique": {},
    "parties_prenantes": [],
    "activites_detaillees": [],
    "chronogramme": [],
    "budget": {},
    "analyse_cout_benefice": {},
    "risques": [],
    "communication": "comm",
    "note_conceptuelle": "",
    "resume_executif": "",
}


async def _fake_stream_ok(project_dict, refs):
    # Emule plusieurs deltas + une validation finale
    for chunk in ("Hel", "lo ", "World"):
        yield ("token", {"chars": len(chunk)})
    yield ("validated", {"content": _FAKE_GENERATED})


async def _fake_stream_truncated(project_dict, refs):
    yield ("token", {"chars": 5})
    raise ValueError("Le modèle a atteint la limite de tokens (4096).")


async def _fake_stream_invalid_json(project_dict, refs):
    yield ("token", {"chars": 1})
    raise json.JSONDecodeError("Expecting value", "doc", 0)


async def _fake_stream_validation_error(project_dict, refs):
    yield ("token", {"chars": 1})
    # On déclenche la même erreur que Pydantic produirait
    from schemas.generated import GeneratedContent
    try:
        GeneratedContent.model_validate({"introduction": "x"})  # manque tout le reste
    except ValidationError as e:
        raise e


# ─── Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_happy_path(monkeypatch):
    monkeypatch.setattr(
        generate_router.ai_service, "stream_project_content", _fake_stream_ok
    )
    monkeypatch.setattr(
        generate_router.docx_service, "create_word_document",
        lambda pd, gen: b"FAKE_DOCX_BYTES",
    )
    monkeypatch.setattr(
        generate_router, "save_project",
        lambda *a, **kw: type("P", (), {"id": 7})(),
    )
    # Désactive le throttling pour capturer chaque progress
    monkeypatch.setattr(generate_router, "_PROGRESS_TICK_SECONDS", 0)

    blob = await _collect(generate_router._generate_events(_project(), user_id=1))
    events = _parse_sse(blob)

    names = [e[0] for e in events]
    # Le pipeline doit toujours émettre dans cet ordre
    assert names[0] == "phase" and events[0][1]["name"] == "generation"
    assert "progress" in names
    assert any(n == "phase" and d["name"] == "docx" for n, d in events)
    assert any(n == "phase" and d["name"] == "persistance" for n, d in events)
    assert names[-1] == "done"

    done_payload = events[-1][1]
    assert done_payload["project_id"] == 7
    assert done_payload["filename"].endswith("_ONZ.docx")
    assert done_payload["chars"] == len("Hello World")


@pytest.mark.asyncio
async def test_stream_truncated_emits_error(monkeypatch):
    monkeypatch.setattr(
        generate_router.ai_service, "stream_project_content", _fake_stream_truncated
    )
    monkeypatch.setattr(generate_router, "_PROGRESS_TICK_SECONDS", 0)

    blob = await _collect(generate_router._generate_events(_project(), user_id=1))
    events = _parse_sse(blob)

    assert events[-1][0] == "error"
    assert "limite de tokens" in events[-1][1]["message"]
    # Ne doit JAMAIS atteindre les phases docx/persistance après une erreur LLM
    assert not any(n == "phase" and d["name"] == "docx" for n, d in events)


@pytest.mark.asyncio
async def test_stream_invalid_json_emits_error(monkeypatch):
    monkeypatch.setattr(
        generate_router.ai_service, "stream_project_content", _fake_stream_invalid_json
    )
    monkeypatch.setattr(generate_router, "_PROGRESS_TICK_SECONDS", 0)

    events = _parse_sse(
        await _collect(generate_router._generate_events(_project(), user_id=1))
    )
    assert events[-1][0] == "error"
    assert "JSON invalide" in events[-1][1]["message"]


@pytest.mark.asyncio
async def test_stream_validation_error_lists_fields(monkeypatch):
    monkeypatch.setattr(
        generate_router.ai_service, "stream_project_content",
        _fake_stream_validation_error,
    )
    monkeypatch.setattr(generate_router, "_PROGRESS_TICK_SECONDS", 0)

    events = _parse_sse(
        await _collect(generate_router._generate_events(_project(), user_id=1))
    )
    assert events[-1][0] == "error"
    msg = events[-1][1]["message"]
    assert "champ(s)" in msg
    # Au moins un des champs requis doit apparaître
    assert "cadre_logique" in msg or "parties_prenantes" in msg


@pytest.mark.asyncio
async def test_stream_persistance_failure_still_completes(monkeypatch):
    """Si save_project lève, on émet quand même `done` (le doc est utile sans persistance)."""
    monkeypatch.setattr(
        generate_router.ai_service, "stream_project_content", _fake_stream_ok
    )
    monkeypatch.setattr(
        generate_router.docx_service, "create_word_document",
        lambda pd, gen: b"FAKE",
    )

    def _boom(*a, **kw):
        raise RuntimeError("disk full")

    monkeypatch.setattr(generate_router, "save_project", _boom)
    monkeypatch.setattr(generate_router, "_PROGRESS_TICK_SECONDS", 0)

    events = _parse_sse(
        await _collect(generate_router._generate_events(_project(), user_id=1))
    )
    assert events[-1][0] == "done"
    assert events[-1][1]["project_id"] is None  # persistance a échoué
