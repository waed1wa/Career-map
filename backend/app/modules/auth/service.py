"""Сценарии модуля: регистрация, вход, «кто я». Прецеденты «Зарегистрироваться» и «Войти»."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.auth.domain import (
    AuthError,
    EmailTakenError,
    User,
    check_password,
    normalize_email,
    parse_role,
)
from app.modules.auth.ports import UserRepository
from app.modules.auth.security import PasswordHasher, TokenError, TokenService

# Одна и та же фраза для «нет такой почты» и «неверный пароль»: не подсказываем, кто зарегистрирован.
WRONG_CREDENTIALS = "Неверная почта или пароль"


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock

    def register(self, email: str, password: str, role: str, consent: bool) -> User:
        if not consent:
            raise AuthError("Без согласия на обработку персональных данных регистрация невозможна")
        email = normalize_email(email)
        check_password(password)
        user_role = parse_role(role)
        if self._users.get_by_email(email) is not None:
            raise EmailTakenError("Пользователь с такой почтой уже есть")
        user = User(
            id=uuid4(),
            email=email,
            password_hash=self._hasher.hash(password),
            role=user_role,
            consent_at=self._clock(),
        )
        self._users.add(user)
        return user

    def login(self, email: str, password: str) -> str:
        try:
            email = normalize_email(email)
        except AuthError:
            raise AuthError(WRONG_CREDENTIALS) from None
        user = self._users.get_by_email(email)
        stored = user.password_hash if user else self._hasher.dummy_hash()
        password_ok = self._hasher.verify(password, stored)
        if user is None or not password_ok:
            raise AuthError(WRONG_CREDENTIALS)
        return self._tokens.issue(str(user.id), user.role)

    def current_user(self, token: str) -> User:
        try:
            payload = self._tokens.read(token)
            user = self._users.get_by_id(UUID(payload["sub"]))
        except (TokenError, ValueError, KeyError):
            raise AuthError("Нужно войти заново") from None
        if user is None:
            raise AuthError("Нужно войти заново")
        return user
