"""Ядро модуля «Вход и роли». Не зависит ни от FastAPI, ни от базы — тестируется отдельно."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

EMAIL_MAX = 254
PASSWORD_MIN = 8
PASSWORD_MAX = 64

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Role(StrEnum):
    """Через регистрацию можно стать только студентом или организатором. Администратора заводим вручную."""

    STUDENT = "student"
    ORGANIZER = "organizer"


class AuthError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


class EmailTakenError(AuthError):
    """Почта уже занята — для API это отдельный ответ 409."""


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str
    role: Role
    consent_at: datetime  # когда дал согласие на обработку персональных данных (152-ФЗ)


def normalize_email(email: str) -> str:
    """Почту храним в одном виде: без пробелов по краям и в нижнем регистре."""
    email = email.strip().lower()
    if not email or len(email) > EMAIL_MAX or not _EMAIL.match(email):
        raise AuthError("Неверный формат почты")
    return email


def check_password(password: str) -> None:
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        raise AuthError(f"Пароль должен быть от {PASSWORD_MIN} до {PASSWORD_MAX} символов")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise AuthError("В пароле нужны хотя бы одна буква и одна цифра")


def parse_role(role: str) -> Role:
    try:
        return Role(role)
    except ValueError:
        raise AuthError("Роль может быть только «студент» или «организатор»") from None
