"""Модуль «Вход и роли»: регистрация, вход, «кто я».

Роутер тонкий: только переводит HTTP в вызовы AuthService и ошибки — в коды ответа.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_session
from app.modules.auth.domain import AuthError, EmailTakenError, User
from app.modules.auth.security import PasswordHasher, TokenService
from app.modules.auth.service import AuthService
from app.modules.auth.sql_repo import SqlUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str
    password: str
    role: str = "student"
    consent: bool = False


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def get_auth_service(session: Annotated[Session, Depends(get_session)]) -> AuthService:
    settings = get_settings()
    tokens = TokenService(settings.secret_key, settings.token_ttl_minutes * 60)
    return AuthService(SqlUserRepository(session), PasswordHasher(), tokens)


ServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def _out(user: User) -> UserOut:
    return UserOut(id=str(user.id), email=user.email, role=user.role.value)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, service: ServiceDep) -> UserOut:
    try:
        user = service.register(data.email, data.password, data.role, data.consent)
    except EmailTakenError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except AuthError as error:
        raise HTTPException(422, str(error)) from error  # 422: данные не прошли правила
    return _out(user)


@router.post("/login")
def login(data: LoginIn, service: ServiceDep) -> TokenOut:
    try:
        return TokenOut(access_token=service.login(data.email, data.password))
    except AuthError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error


@router.get("/me")
def me(service: ServiceDep, authorization: Annotated[str | None, Header()] = None) -> UserOut:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Нужно войти")
    try:
        return _out(service.current_user(authorization.removeprefix("Bearer ")))
    except AuthError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error
