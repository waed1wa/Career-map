"""Заявка на проект. Здесь живут два инварианта из архитектуры:

1. Отказ только с причиной.
2. За 7 дней организатор отвечает, иначе заявка «просрочена». На 5-й день — напоминание.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

REMINDER_AFTER = timedelta(days=5)
DEADLINE_AFTER = timedelta(days=7)


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApplicationError(Exception):
    """Нарушено правило заявки."""


@dataclass
class Application:
    student_id: str
    project_id: str
    submitted_at: datetime
    status: ApplicationStatus = ApplicationStatus.SUBMITTED
    reject_reason: str | None = None
    reminder_sent: bool = field(default=False)

    @property
    def deadline(self) -> datetime:
        return self.submitted_at + DEADLINE_AFTER

    def accept(self) -> None:
        self._ensure_open()
        self.status = ApplicationStatus.ACCEPTED

    def reject(self, reason: str) -> None:
        self._ensure_open()
        if not reason or len(reason.strip()) < 10:
            raise ApplicationError("Отказ без причины запрещён: напишите хотя бы одно предложение")
        self.status = ApplicationStatus.REJECTED
        self.reject_reason = reason.strip()

    def needs_reminder(self, now: datetime) -> bool:
        """Напомнить организатору: прошло 5 дней, ответа нет, напоминания ещё не было."""
        return (
            self.status == ApplicationStatus.SUBMITTED
            and not self.reminder_sent
            and now - self.submitted_at >= REMINDER_AFTER
        )

    def expire_if_overdue(self, now: datetime) -> bool:
        """Вызывает планировщик раз в час. Возвращает True, если заявка только что стала просроченной."""
        if self.status == ApplicationStatus.SUBMITTED and now >= self.deadline:
            self.status = ApplicationStatus.EXPIRED
            return True
        return False

    def _ensure_open(self) -> None:
        if self.status != ApplicationStatus.SUBMITTED:
            raise ApplicationError(f"Заявка уже закрыта: {self.status}")
