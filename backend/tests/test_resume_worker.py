"""Фоновая задача parse_resume. Тесты идут в CI, где установлен Celery."""

from pathlib import Path

import pytest

pytest.importorskip("celery")

from app import worker  # noqa: E402
from app.modules.profile.memory import InMemoryStorage  # noqa: E402

PDF = (Path(__file__).parent / "fixtures" / "resume_text.pdf").read_bytes()


@pytest.fixture
def storage(monkeypatch):
    memory = InMemoryStorage()
    monkeypatch.setattr(worker.MinioResumeStorage, "from_settings", classmethod(lambda cls, s: memory))
    return memory


def test_task_returns_skills_and_deletes_file(storage):
    storage.put("guest/a.pdf", PDF, "application/pdf")

    result = worker.parse_resume("guest/a.pdf", "cv.pdf")

    assert {"id": "sql", "title": "SQL и базы данных", "matched": "PostgreSQL"} in result["skills"]
    assert storage.files == {}


def test_task_returns_error_text_for_bad_file(storage):
    storage.put("guest/b.pdf", b"%PDF-1.7\n" + b"\x00" * 100, "application/pdf")

    result = worker.parse_resume("guest/b.pdf", "cv.pdf")

    assert "Не получилось прочитать PDF" in result["error"]
    assert storage.files == {}
