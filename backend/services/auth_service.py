import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

# bcrypt — limite stricte de 72 octets sur le secret (protocole). On valide en amont.
_BCRYPT_MAX_BYTES = 72

# JWT — HS256 avec secret partagé (suffisant pour un service unique sans fédération)
_JWT_ALGORITHM = "HS256"
_DEFAULT_EXPIRE_MINUTES = 60 * 24  # 24h


def _get_secret() -> str:
    """Lue à chaque appel pour permettre le hot-reload en dev."""
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY n'est pas défini. Ajoute-le dans backend/.env "
            "(générer avec : python -c \"import secrets; print(secrets.token_urlsafe(64))\")."
        )
    if len(secret) < 32:
        logger.warning("JWT_SECRET_KEY court (%d caractères) — recommandé : >= 64.", len(secret))
    return secret


def _get_expire_minutes() -> int:
    return int(os.getenv("JWT_EXPIRE_MINUTES", _DEFAULT_EXPIRE_MINUTES))


class PasswordTooLongError(ValueError):
    """Levé si le mot de passe encodé dépasse 72 octets (limite bcrypt)."""


def _encode(plain: str) -> bytes:
    data = plain.encode("utf-8")
    if len(data) > _BCRYPT_MAX_BYTES:
        raise PasswordTooLongError(
            f"Le mot de passe ne peut pas dépasser {_BCRYPT_MAX_BYTES} octets (encodé UTF-8)."
        )
    return data


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_encode(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))
    except (ValueError, TypeError):
        # Hash invalide / corrompu — refuse silencieusement
        return False


def create_access_token(*, user_id: int, email: str, expires_minutes: Optional[int] = None) -> tuple[str, int]:
    """Retourne (token, expires_in_seconds)."""
    minutes = expires_minutes if expires_minutes is not None else _get_expire_minutes()
    expires_delta = timedelta(minutes=minutes)
    expire_at = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, _get_secret(), algorithm=_JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_token(token: str) -> dict:
    """Décode un JWT. Lève JWTError si invalide/expiré."""
    return jwt.decode(token, _get_secret(), algorithms=[_JWT_ALGORITHM])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "JWTError",
    "PasswordTooLongError",
]
