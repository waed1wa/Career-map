"""Согласие на обработку персональных данных в таблице users (152-ФЗ).

Таблица users пока пустая (регистрации до этой миграции не было), поэтому колонку
сразу делаем обязательной.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    op.drop_column("users", "consent_at")
