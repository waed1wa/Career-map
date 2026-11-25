"""Порты модуля «Профиль»: где лежит файл резюме и кто его разбирает в фоне.

Реализации: MinIO и Celery на стенде, в памяти — в тестах. Логика разбора о них не знает.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.modules.profile.skill_finder import FoundSkill


class ResumeStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class JobState(StrEnum):
    PENDING = "pending"  # в очереди или разбирается
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class JobStatus:
    state: JobState
    skills: tuple[FoundSkill, ...] = ()
    error: str | None = None


class ParseQueue(Protocol):
    def submit(self, key: str, filename: str) -> str:
        """Ставит разбор в очередь и сразу возвращает номер задачи."""
        ...

    def status(self, job_id: str) -> JobStatus: ...
