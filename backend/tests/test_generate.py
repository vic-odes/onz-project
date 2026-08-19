"""Tests du endpoint bloquant `routers/generate.generate_document`.

On mocke :
- `ai_service.generate_project_content` (coroutine) — pas d'appel LLM réel,
- `docx_service.create_word_document` — pour ne pas dépendre de python-docx,
- `database.save_project` — pour ne pas toucher à SQLite/Alembic.

La fonction de route est appelée directement en injectant un `current_user`
factice (on court-circuite ainsi la dépendance FastAPI `get_current_user`).
"""
from __future__ import annotations

import json

import pytest
from fastapi import HTTPException
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


class _FakeUser:
    id = 1
    nom = "Testeur"


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


async def _fake_generate_ok(project_dict, refs):
    return _FAKE_GENERATED


async def _read_body(response) -> bytes:
    out = bytearray()
    async for chunk in response.body_iterator:
        out.extend(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
    return bytes(out)


@pytest.mark.asyncio
async def test_generate_happy_path(monkeypatch):
    monkeypatch.setattr(generate_router.ai_service, "generate_project_content", _fake_generate_ok)
    monkeypatch.setattr(
        generate_router.docx_service, "create_word_document",
        lambda pd, gen: b"FAKE_DOCX_BYTES",
    )
    saved = {}

    class _FakeSavedProject:
        id = 42

    def _fake_save_project(pd, gen, uid, docx):
        saved.update(uid=uid, docx=docx)
        return _FakeSavedProject()

    monkeypatch.setattr(generate_router, "save_project", _fake_save_project)

    response = await generate_router.generate_document(_project(), current_user=_FakeUser())

    assert response.media_type == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert 'attachment; filename="Projet_Test_ONZ.docx"' in response.headers["content-disposition"]
    assert await _read_body(response) == b"FAKE_DOCX_BYTES"
    # La persistance reçoit bien l'id utilisateur et les octets du document
    assert saved["uid"] == 1 and saved["docx"] == b"FAKE_DOCX_BYTES"
    # L'id du projet créé est exposé pour permettre au frontend d'enchaîner sur
    # une recherche de financement.
    assert response.headers["x-project-id"] == "42"


@pytest.mark.asyncio
async def test_generate_invalid_json_returns_502(monkeypatch):
    async def _boom(project_dict, refs):
        raise json.JSONDecodeError("Expecting value", "doc", 0)

    monkeypatch.setattr(generate_router.ai_service, "generate_project_content", _boom)

    with pytest.raises(HTTPException) as exc:
        await generate_router.generate_document(_project(), current_user=_FakeUser())
    assert exc.value.status_code == 502
    assert "JSON invalide" in exc.value.detail


@pytest.mark.asyncio
async def test_generate_validation_error_lists_fields(monkeypatch):
    async def _bad_shape(project_dict, refs):
        from schemas.generated import GeneratedContent
        GeneratedContent.model_validate({"introduction": "x"})  # manque tout le reste

    monkeypatch.setattr(generate_router.ai_service, "generate_project_content", _bad_shape)

    with pytest.raises(HTTPException) as exc:
        await generate_router.generate_document(_project(), current_user=_FakeUser())
    assert exc.value.status_code == 502
    assert "champ(s)" in exc.value.detail


@pytest.mark.asyncio
async def test_generate_persistance_failure_still_returns_docx(monkeypatch):
    """Si save_project lève, on renvoie quand même le .docx (persistance non bloquante)."""
    monkeypatch.setattr(generate_router.ai_service, "generate_project_content", _fake_generate_ok)
    monkeypatch.setattr(
        generate_router.docx_service, "create_word_document",
        lambda pd, gen: b"FAKE",
    )

    def _disk_full(*a, **kw):
        raise RuntimeError("disk full")

    monkeypatch.setattr(generate_router, "save_project", _disk_full)

    response = await generate_router.generate_document(_project(), current_user=_FakeUser())
    assert await _read_body(response) == b"FAKE"
