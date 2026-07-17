from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Réponse d'authentification. Le JWT est posé dans un cookie httpOnly côté
    serveur — il n'apparaît JAMAIS dans le corps de la réponse (protection XSS)."""
    expires_in: int  # secondes
    user: UserResponse
