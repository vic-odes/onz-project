"""Tests d'intégration du flux d'authentification (endpoints réels + DB SQLite).

Vérifie :
- register/login posent un cookie de session httpOnly (le JWT n'est jamais dans
  le corps de la réponse),
- /me exige la session (cookie) et la refuse sinon,
- logout expire le cookie,
- le rate-limiting bloque le brute-force sur /login.

Base de données : SQLite temporaire, `get_db` surchargé. On n'entre pas dans le
context manager de TestClient → l'événement startup (init_db/alembic) ne se
déclenche pas ; on crée le schéma directement via `Base.metadata.create_all`.
"""
from __future__ import annotations

import os

# Cookie non-Secure pour que le client de test (http://testserver) le renvoie.
os.environ["AUTH_COOKIE_SECURE"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from database import Base, get_db
from services.auth_service import COOKIE_NAME
import models.user  # noqa: F401 — enregistre la table users dans Base.metadata
import models.project  # noqa: F401 — enregistre la table projects
from rate_limit import limiter


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
    limiter.enabled = False  # désactivé pour les tests fonctionnels
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()
        limiter.enabled = False


_CREDS = {"email": "victor@test.org", "password": "motdepasse123", "full_name": "Victor"}


def _set_cookie_header(response) -> str:
    return response.headers.get("set-cookie", "").lower()


def test_register_sets_httponly_cookie_no_token_in_body(client):
    r = client.post("/api/auth/register", json=_CREDS)
    assert r.status_code == 201, r.text
    body = r.json()
    # Le token ne doit JAMAIS apparaître dans le corps
    assert "access_token" not in body
    assert body["user"]["email"] == "victor@test.org"
    assert body["expires_in"] > 0
    # Cookie de session httpOnly
    cookie = _set_cookie_header(r)
    assert COOKIE_NAME in cookie and "httponly" in cookie


def test_me_requires_session(client):
    # Sans cookie → 401
    assert client.get("/api/auth/me").status_code == 401


def test_login_then_me_then_logout(client):
    client.post("/api/auth/register", json=_CREDS)
    client.cookies.clear()  # repart d'une session vierge

    r = client.post("/api/auth/login", json={"email": _CREDS["email"], "password": _CREDS["password"]})
    assert r.status_code == 200, r.text
    assert "access_token" not in r.json()
    assert COOKIE_NAME in _set_cookie_header(r)

    # Le cookie posé par login permet d'accéder à /me
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "victor@test.org"

    # logout expire le cookie
    out = client.post("/api/auth/logout")
    assert out.status_code == 200
    logout_cookie = _set_cookie_header(out)
    assert COOKIE_NAME in logout_cookie and ("max-age=0" in logout_cookie or "expires=" in logout_cookie)


def test_login_wrong_password_is_401(client):
    client.post("/api/auth/register", json=_CREDS)
    r = client.post("/api/auth/login", json={"email": _CREDS["email"], "password": "mauvais"})
    assert r.status_code == 401


def test_login_is_rate_limited(client):
    limiter.enabled = True
    try:
        statuses = [
            client.post(
                "/api/auth/login",
                json={"email": "inconnu@test.org", "password": "peu-importe"},
            ).status_code
            for _ in range(7)
        ]
    finally:
        limiter.enabled = False

    # Les premières tentatives passent (mauvais identifiants → 401),
    # puis le limiteur renvoie 429.
    assert statuses.count(401) <= 5
    assert 429 in statuses
