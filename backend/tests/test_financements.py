"""Tests d'intégration du router `financements` (endpoints réels + DB SQLite).

Même pattern que `test_auth_flow.py` : DB SQLite temporaire, `get_db` surchargé,
TestClient réel. `financement_service.rechercher_financements` est mocké — pas
d'appel LLM réel.
"""
from __future__ import annotations

import os

os.environ["AUTH_COOKIE_SECURE"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from database import Base, get_db
from rate_limit import limiter
from routers import financements as financements_router
from schemas.financement import ResultatsFinancement
import models.user  # noqa: F401
import models.project  # noqa: F401
import models.financement  # noqa: F401
from models.project import Project


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = _override_get_db
    limiter.enabled = False
    tc = TestClient(main.app)
    tc.testing_session_factory = TestingSession
    try:
        yield tc
    finally:
        main.app.dependency_overrides.clear()


_CREDS = {"email": "vic@test.org", "password": "motdepasse123", "full_name": "Vic"}


def _register(client) -> int:
    client.post("/api/auth/register", json=_CREDS)
    return client.get("/api/auth/me").json()["id"]


def _insert_project(client, user_id: int) -> int:
    db = client.testing_session_factory()
    try:
        project = Project(
            user_id=user_id,
            nom="Adduction eau Makénéné",
            pays="Cameroun",
            secteur="Eau & Assainissement",
            bailleur="Recherche automatique de bailleur",
            probleme_principal="Accès limité à l'eau potable",
            objectif_global="Améliorer l'accès à l'eau potable",
            budget_total=1200000,
            duree_mois=36,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project.id
    finally:
        db.close()


_FAKE_RESULTATS = ResultatsFinancement.model_validate({
    "resume": "3 opportunités identifiées, dont une très compatible.",
    "opportunites": [
        {
            "bailleur": "AFD",
            "programme": "Programme Eau Afrique",
            "categorie": "tres_compatible",
            "score_compatibilite": 91,
            "montant_min": 100000,
            "montant_max": 600000,
            "devise": "EUR",
            "date_limite": "30/11/2026",
            "raisons_compatibilite": ["Cameroun éligible", "Eau potable éligible"],
            "points_vigilance": ["Cofinancement de 30 % nécessaire"],
            "source_officielle": "https://www.afd.fr",
            "fiabilite": "verifie",
            "date_verification": "19/08/2026",
        },
    ],
})


async def _fake_ok(project_data):
    return _FAKE_RESULTATS, True


def test_rechercher_financement_happy_path(client, monkeypatch):
    monkeypatch.setattr(financements_router.financement_service, "rechercher_financements", _fake_ok)
    user_id = _register(client)
    project_id = _insert_project(client, user_id)

    r = client.post(f"/api/financements/rechercher/{project_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert body["project_nom"] == "Adduction eau Makénéné"
    assert body["recherche_live"] is True
    assert len(body["resultats"]["opportunites"]) == 1
    assert body["resultats"]["opportunites"][0]["bailleur"] == "AFD"

    recherche_id = body["id"]

    # GET par id renvoie le même contenu
    r2 = client.get(f"/api/financements/{recherche_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == recherche_id

    # GET par projet liste la recherche (résumé)
    r3 = client.get(f"/api/financements/projet/{project_id}")
    assert r3.status_code == 200
    summaries = r3.json()
    assert len(summaries) == 1
    assert summaries[0]["nb_opportunites"] == 1
    assert "compatible" in summaries[0]["resume"]


def test_rechercher_financement_foreign_project_is_404(client, monkeypatch):
    monkeypatch.setattr(financements_router.financement_service, "rechercher_financements", _fake_ok)
    user_a = _register(client)
    project_id = _insert_project(client, user_a)

    client.cookies.clear()
    client.post("/api/auth/register", json={"email": "autre@test.org", "password": "motdepasse123"})

    r = client.post(f"/api/financements/rechercher/{project_id}")
    assert r.status_code == 404


def test_rechercher_financement_requires_auth(client):
    r = client.post("/api/financements/rechercher/1")
    assert r.status_code == 401


def test_get_recherche_unknown_id_is_404(client):
    _register(client)
    r = client.get("/api/financements/999")
    assert r.status_code == 404


def test_rechercher_financement_llm_error_is_502(client, monkeypatch):
    import json as json_module

    async def _boom(project_data):
        raise json_module.JSONDecodeError("Expecting value", "doc", 0)

    monkeypatch.setattr(financements_router.financement_service, "rechercher_financements", _boom)
    user_id = _register(client)
    project_id = _insert_project(client, user_id)

    r = client.post(f"/api/financements/rechercher/{project_id}")
    assert r.status_code == 502


def test_importer_et_rechercher_happy_path(client, monkeypatch):
    """Un projet monté hors de l'application (PDF importé) peut être recherché
    sans passer par le Stepper — /importer crée un projet minimal (sans docx)."""
    monkeypatch.setattr(financements_router.financement_service, "rechercher_financements", _fake_ok)
    _register(client)

    r = client.post("/api/financements/importer", json={
        "nom": "Projet importé depuis PDF",
        "pays": "Sénégal",
        "secteur": "Agriculture",
        "probleme_principal": "Faible rendement agricole",
        "objectif_global": "Améliorer les rendements",
        "budget_total": 300000,
        "duree_mois": 24,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_nom"] == "Projet importé depuis PDF"
    assert body["resultats"]["opportunites"][0]["bailleur"] == "AFD"

    # Le projet créé n'a pas de docx — il apparaît quand même dans /api/projects/
    projects = client.get("/api/projects/").json()
    imported = next(p for p in projects if p["nom"] == "Projet importé depuis PDF")
    assert imported["bailleur"] == "Recherche automatique de bailleur"
    assert imported["docx_path"] is None


def test_importer_et_rechercher_defaults_secteur_when_missing(client, monkeypatch):
    monkeypatch.setattr(financements_router.financement_service, "rechercher_financements", _fake_ok)
    _register(client)

    r = client.post("/api/financements/importer", json={"nom": "Projet minimal", "pays": "Mali"})
    assert r.status_code == 200, r.text

    projects = client.get("/api/projects/").json()
    imported = next(p for p in projects if p["nom"] == "Projet minimal")
    assert imported["secteur"] == "Non précisé"


def test_importer_et_rechercher_requires_nom_and_pays(client):
    _register(client)
    r = client.post("/api/financements/importer", json={"nom": "", "pays": "Mali"})
    assert r.status_code == 422
