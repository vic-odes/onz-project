"""Tests du service d'authentification (hash + JWT).

JWT_SECRET_KEY est défini dans conftest.py pour les tests.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest

from services.auth_service import (
    JWTError,
    PasswordTooLongError,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_then_verify():
    h = hash_password("p@ssw0rd")
    assert h != "p@ssw0rd"
    assert verify_password("p@ssw0rd", h) is True


def test_verify_rejects_wrong_password():
    h = hash_password("correct")
    assert verify_password("wrong", h) is False


def test_verify_corrupt_hash_returns_false():
    """Un hash corrompu ne doit pas exploser, juste renvoyer False."""
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_hash_rejects_long_password():
    too_long = "x" * 100  # > 72 octets bcrypt
    with pytest.raises(PasswordTooLongError):
        hash_password(too_long)


def test_token_round_trip():
    token, expires_in = create_access_token(user_id=42, email="a@b.fr")
    assert isinstance(token, str)
    assert expires_in > 0
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "a@b.fr"


def test_token_expired_rejected():
    """Token avec expires_minutes négatif → JWTError au décodage."""
    token, _ = create_access_token(user_id=1, email="x@y.fr", expires_minutes=-1)
    # Garantir que la clock a bougé
    time.sleep(0.01)
    with pytest.raises(JWTError):
        decode_token(token)


def test_token_tampered_rejected():
    token, _ = create_access_token(user_id=1, email="x@y.fr")
    # Inverser le dernier caractère du payload pour casser la signature
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(JWTError):
        decode_token(tampered)


def test_expires_in_matches_minutes():
    _, expires_in = create_access_token(user_id=1, email="x@y.fr", expires_minutes=10)
    assert 590 <= expires_in <= 600  # ~10 min, marge pour la latence
