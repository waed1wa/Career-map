"""Адаптер порта UserRepository для PostgreSQL (таблица users из ER-диаграммы)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.modules.auth.domain import Role, User


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student', 'organizer')", name="users_role_check"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def _to_user(row: UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        role=Role(row.role),
        consent_at=row.consent_at,
    )


class SqlUserRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalar(select(UserRow).where(UserRow.email == email))
        return _to_user(row) if row else None

    def get_by_id(self, user_id: UUID) -> User | None:
        row = self._session.get(UserRow, user_id)
        return _to_user(row) if row else None

    def add(self, user: User) -> None:
        self._session.add(
            UserRow(
                id=user.id,
                email=user.email,
                password_hash=user.password_hash,
                role=user.role.value,
                consent_at=user.consent_at,
            )
        )
        self._session.commit()
