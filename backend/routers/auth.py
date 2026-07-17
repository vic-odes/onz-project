import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from schemas.user import UserCreate, UserLogin, UserResponse, Token
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    PasswordTooLongError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
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
    return Token(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    email_norm = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email_norm).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Message volontairement ambigu pour ne pas révéler l'existence du compte
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé.")

    token, expires_in = create_access_token(user_id=user.id, email=user.email)
    logger.info("Connexion réussie — id=%d email=%s", user.id, user.email)
    return Token(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
