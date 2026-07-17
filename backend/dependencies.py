import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.auth_service import decode_token, JWTError, COOKIE_NAME

logger = logging.getLogger(__name__)


def _extract_token(request: Request) -> Optional[str]:
    """Récupère le JWT : d'abord le cookie httpOnly (front web), sinon l'en-tête
    `Authorization: Bearer` (clients API, Swagger, tests)."""
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):].strip() or None
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = _extract_token(request)
    if not token:
        raise credentials_exc
    try:
        payload = decode_token(token)
    except JWTError as e:
        logger.debug("JWT rejeté : %s", e)
        raise credentials_exc

    sub = payload.get("sub")
    if not sub:
        raise credentials_exc
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise credentials_exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exc
    return user
