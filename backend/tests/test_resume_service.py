"""Загрузка и разбор резюме в фоне. Главное правило: файл гостя не остаётся в хранилище."""

from pathlib import Path

import pytest

from app.modules.catalog.repository import load_catalog
from app.modules.profile.memory import ImmediateQueue, InMemoryStorage
from app.modules.profile.ports import JobState
from app.modules.profile.resume_file import ResumeFileError
from app.modules.profile.resume_service import ResumeService, parse_stored_resume
from app.modules.profile.skill_finder import SkillFinder

PDF = (Path(__file__).parent / "fixtures" / "resume_text.pdf").read_bytes()
finder = SkillFinder(load_catalog())


def make() -> tuple[ResumeService, InMemoryStorage, ImmediateQueue]:
    storage = InMemoryStorage()
    queue = ImmediateQueue(storage, finder)
    return ResumeService(storage, queue), storage, queue


def test_resume_goes_through_queue_to_skills():
    service, storage, queue = make()

    job_id = service.upload("cv.pdf", PDF, consent=True)
    status = queue.status(job_id)

    assert status.state == JobState.DONE
    assert [s.skill.value for s in status.skills] == [
        "git",
        "python",
        "sql",
        "http-api",
        "web-framework",
        "testing",  # из слов «для автотестов» в шапке тестового файла
        "docker",
    ]


def test_file_is_deleted_after_parsing():
    service, storage, _ = make()

    service.upload("cv.pdf", PDF, consent=True)

    assert storage.files == {}


def test_file_is_deleted_even_if_parsing_failed():
    storage = InMemoryStorage()
    storage.put("guest/broken.pdf", b"%PDF-1.7\n" + b"\x00" * 100, "application/pdf")

    with pytest.raises(ResumeFileError):
        parse_stored_resume(storage, finder, "guest/broken.pdf", "cv.pdf")

    assert storage.files == {}


def test_failed_parsing_is_shown_as_status():
    service, _, queue = make()

    job_id = service.upload("cv.pdf", b"%PDF-1.7\n" + b"\x00" * 100, consent=True)

    status = queue.status(job_id)
    assert status.state == JobState.FAILED
    assert status.error is not None and "Не получилось прочитать PDF" in status.error


def test_no_consent_no_upload():
    service, storage, _ = make()

    with pytest.raises(ResumeFileError, match="нужно согласие"):
        service.upload("cv.pdf", PDF, consent=False)
    assert storage.files == {}


def test_bad_file_is_not_stored_at_all():
    service, storage, _ = make()

    with pytest.raises(ResumeFileError, match="PDF или DOCX"):
        service.upload("photo.jpg", b"\xff\xd8\xff" + b"\x00" * 100, consent=True)
    assert storage.files == {}


def test_student_file_name_is_not_in_storage_key():
    """Имя файла часто «Иванов_Иван_резюме.pdf» — в хранилище оно попасть не должно."""
    storage = InMemoryStorage()
    keys: list[str] = []

    class RememberKey:
        def submit(self, key: str, filename: str) -> str:
            keys.append(key)
            return "job"

        def status(self, job_id: str):
            raise NotImplementedError

    ResumeService(storage, RememberKey()).upload("Иванов_Иван_резюме.pdf", PDF, consent=True)

    assert keys[0].startswith("guest/") and keys[0].endswith(".pdf")
    assert "Иванов" not in keys[0]


def test_unknown_job_is_pending():
    _, _, queue = make()

    assert queue.status("no-such-job").state == JobState.PENDING
