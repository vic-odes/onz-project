"""Tests d'intégration du flux de génération asynchrone (`POST /api/generate/demarrer`
+ `GET /api/generate/etat/{id}`). Même pattern que `test_financements.py` : DB SQLite
temporaire, `get_db` surchargé, TestClient réel. `ai_service.generate_project_content`
et `docx_service.create_word_document` sont mockés — pas d'appel LLM réel.
"""
from __future__ import annotations

import os

os.environ["AUTH_COOKIE_SECURE"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database
import main
from database import Base, get_db
from rate_limit import limiter
from routers import generate as generate_router
import models.user  # noqa: F401
import models.project  # noqa: F401
import models.financement  # noqa: F401
import models.generation  # noqa: F401


@pytest.fixture
def client(tmp_path, monkeypatch):
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
    # La tâche de fond de génération appelle SessionLocal() directement (pas
    # Depends(get_db), puisqu'elle tourne après la fin de la requête) — la
    # rediriger elle aussi vers la DB de test, sinon elle écrit dans la DB globale.
    # Deux points d'appel à rediriger : le module `generate` (requêtes sur le
    # job) et le module `database` lui-même (`save_project`, qui résout
    # `SessionLocal` dans son propre espace de noms au moment de l'appel).
    monkeypatch.setattr(generate_router, "SessionLocal", TestingSession)
    monkeypatch.setattr(database, "SessionLocal", TestingSession)
    limiter.enabled = False
    tc = TestClient(main.app)
    tc.testing_session_factory = TestingSession
    try:
        yield tc
    finally:
        main.app.dependency_overrides.clear()


_CREDS = {"email": "vic@test.org", "password": "motdepasse123", "full_name": "Vic"}

_PROJECT_PAYLOAD = {
    "nom": "Adduction eau Makénéné",
    "pays": "Cameroun",
    "secteur": "Eau & Assainissement",
    "bailleur": "AFD",
    "probleme_principal": "Accès limité à l'eau potable",
    "objectif_global": "Améliorer l'accès à l'eau potable",
    "budget_total": 1200000,
    "duree_mois": 36,
}

_FAKE_GENERATED = {
    "introduction": "Texte d'introduction.",
    "cadre_logique": {},
    "parties_prenantes": [],
    "activites_detaillees": [],
    "chronogramme": [],
    "budget": {},
    "analyse_cout_benefice": {},
    "risques": [],
    "communication": {},
}


def _register(client) -> int:
    client.post("/api/auth/register", json=_CREDS)
    return client.get("/api/auth/me").json()["id"]


async def _fake_generate_ok(project_dict, reference_pdfs=None):
    return dict(_FAKE_GENERATED)


def test_demarrer_generation_happy_path(client, monkeypatch):
    """La génération s'exécute en arrière-plan : la réponse du POST est un
    instantané pris AVANT que la tâche de fond ne s'exécute — elle montre donc
    toujours status="en_cours", même si (comme ici, sous TestClient) la tâche
    a déjà terminé quand le POST revient. Le résultat final s'obtient via GET."""
    monkeypatch.setattr(generate_router.ai_service, "generate_project_content", _fake_generate_ok)
    monkeypatch.setattr(generate_router.docx_service, "create_word_document", lambda *a, **k: b"fake-docx-bytes")
    _register(client)

    r = client.post("/api/generate/demarrer", json=_PROJECT_PAYLOAD)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "en_cours"
    assert body["project_id"] is None
    job_id = body["id"]

    r2 = client.get(f"/api/generate/etat/{job_id}")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["status"] == "termine"
    assert body2["project_id"] is not None
    assert body2["erreur"] is None

    # Le projet a bien été persisté avec le docx généré en arrière-plan.
    r3 = client.get(f"/api/projects/{body2['project_id']}")
    assert r3.status_code == 200
    assert r3.json()["nom"] == "Adduction eau Makénéné"

    r4 = client.get(f"/api/projects/{body2['project_id']}/download")
    assert r4.status_code == 200
    assert r4.content == b"fake-docx-bytes"


def test_demarrer_generation_llm_error_sets_status_erreur(client, monkeypatch):
    """L'échec de la génération se produit désormais dans la tâche de fond — le
    POST renvoie toujours 200 (démarrage réussi), l'échec se lit via GET."""
    async def _boom(project_dict, reference_pdfs=None):
        raise ValueError("Le modèle a atteint la limite de tokens (8000) — réponse tronquée.")

    monkeypatch.setattr(generate_router.ai_service, "generate_project_content", _boom)
    _register(client)

    r = client.post("/api/generate/demarrer", json=_PROJECT_PAYLOAD)
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]

    r2 = client.get(f"/api/generate/etat/{job_id}")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["status"] == "erreur"
    assert "limite de tokens" in body2["erreur"]
    assert body2["project_id"] is None


def test_demarrer_generation_requires_auth(client):
    r = client.post("/api/generate/demarrer", json=_PROJECT_PAYLOAD)
    assert r.status_code == 401


def test_etat_generation_unknown_id_is_404(client):
    _register(client)
    r = client.get("/api/generate/etat/999")
    assert r.status_code == 404


def test_etat_generation_foreign_job_is_404(client, monkeypatch):
    monkeypatch.setattr(generate_router.ai_service, "generate_project_content", _fake_generate_ok)
    monkeypatch.setattr(generate_router.docx_service, "create_word_document", lambda *a, **k: b"fake-docx-bytes")
    _register(client)
    r = client.post("/api/generate/demarrer", json=_PROJECT_PAYLOAD)
    job_id = r.json()["id"]

    client.cookies.clear()
    client.post("/api/auth/register", json={"email": "autre@test.org", "password": "motdepasse123"})

    r2 = client.get(f"/api/generate/etat/{job_id}")
    assert r2.status_code == 404
