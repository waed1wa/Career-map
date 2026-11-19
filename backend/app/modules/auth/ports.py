"""Порт хранилища пользователей. Адаптеры: в памяти (тесты) и PostgreSQL (стенд)."""

from typing import Protocol
from uuid import UUID

from app.modules.auth.domain import User


class UserRepository(Protocol):
    def get_by_email(self, email: str) -> User | None: ...

    def get_by_id(self, user_id: UUID) -> User | None: ...

    def add(self, user: User) -> None: ...


class InMemoryUserRepository:
    """Хранилище в памяти для тестов и локальных экспериментов."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, User] = {}

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._by_id.get(user_id)

    def add(self, user: User) -> None:
        self._by_id[user.id] = user
