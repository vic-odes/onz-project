import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from rate_limit import limiter, LOGIN_RATE_LIMIT, REGISTER_RATE_LIMIT
from schemas.user import UserCreate, UserLogin, UserResponse, SessionResponse
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    PasswordTooLongError,
    COOKIE_NAME,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _cookie_flags() -> tuple[bool, str]:
    """(secure, samesite) — configurables selon l'environnement de déploiement.

    - `AUTH_COOKIE_SECURE` (défaut true) : n'envoie le cookie qu'en HTTPS. Les
      navigateurs modernes acceptent malgré tout les cookies Secure sur
      http://localhost, donc le défaut sécurisé n'entrave pas le dev local.
    - `AUTH_COOKIE_SAMESITE` (défaut "lax") : "lax" bloque l'envoi du cookie sur
      les requêtes POST cross-site → protection CSRF. Passer à "none" (avec
      secure=true) si le front et l'API sont sur des domaines réellement distincts.
    """
    secure = os.getenv("AUTH_COOKIE_SECURE", "true").lower() != "false"
    samesite = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
    return secure, samesite


def _set_auth_cookie(response: Response, token: str, max_age: int) -> None:
    secure, samesite = _cookie_flags()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,      # inaccessible au JavaScript → immunité au vol par XSS
        secure=secure,
        samesite=samesite,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    secure, samesite = _cookie_flags()
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
    )


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_RATE_LIMIT)
def register(request: Request, response: Response, payload: UserCreate, db: Session = Depends(get_db)):
    email_norm = payload.email.lower().strip()
    existing = db.query(User).filter(User.email == email_norm).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cet email est déjà enregistré.")

    try:
        hashed = hash_password(payload.password)
    except PasswordTooLongError as e:
        raise HTTPException(status_code=422, detail=str(e))

    user = User(
        email=email_norm,
        hashed_password=hashed,
        full_name=(payload.full_name or "").strip() or None,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cet email est déjà enregistré.")
    db.refresh(user)
    logger.info("Nouvel utilisateur enregistré — id=%d email=%s", user.id, user.email)

    token, expires_in = create_access_token(user_id=user.id, email=user.email)
    _set_auth_cookie(response, token, expires_in)
    return SessionResponse(expires_in=expires_in, user=UserResponse.model_validate(user))


@router.post("/login", response_model=SessionResponse)
@limiter.limit(LOGIN_RATE_LIMIT)
def login(request: Request, response: Response, payload: UserLogin, db: Session = Depends(get_db)):
    email_norm = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email_norm).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Message volontairement ambigu pour ne pas révéler l'existence du compte
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé.")

    token, expires_in = create_access_token(user_id=user.id, email=user.email)
    _set_auth_cookie(response, token, expires_in)
    logger.info("Connexion réussie — id=%d email=%s", user.id, user.email)
    return SessionResponse(expires_in=expires_in, user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response):
    """Invalide la session côté client en supprimant le cookie httpOnly."""
    _clear_auth_cookie(response)
    return {"detail": "Déconnecté."}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
