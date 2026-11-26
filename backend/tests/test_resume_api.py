"""API загрузки резюме. Тесты идут в CI, где установлен FastAPI.

MinIO и Celery подменяем версиями в памяти: проверяем сам API, а не контейнеры.
"""

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.modules.catalog.repository import load_catalog  # noqa: E402
from app.modules.profile.memory import ImmediateQueue, InMemoryStorage  # noqa: E402
from app.modules.profile.resume_service import ResumeService  # noqa: E402
from app.modules.profile.router import get_resume_service  # noqa: E402
from app.modules.profile.skill_finder import SkillFinder  # noqa: E402

PDF = (Path(__file__).parent / "fixtures" / "resume_text.pdf").read_bytes()


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def client(storage: InMemoryStorage) -> TestClient:
    app = create_app()
    service = ResumeService(storage, ImmediateQueue(storage, SkillFinder(load_catalog())))
    app.dependency_overrides[get_resume_service] = lambda: service
    return TestClient(app)


def upload(client: TestClient, name: str, data: bytes, consent: bool = True):
    return client.post(
        "/api/profile/resume",
        files={"file": (name, data, "application/octet-stream")},
        data={"consent": "true" if consent else "false"},
    )


def test_upload_then_status_with_skills(client, storage):
    response = upload(client, "cv.pdf", PDF)

    assert response.status_code == 202
    status = client.get(f"/api/profile/resume/{response.json()['job_id']}").json()
    assert status["status"] == "done"
    assert {
        "id": "sql",
        "title": "SQL и базы данных",
        "matched": "PostgreSQL",
        "source": "dictionary",
    } in status["skills"]
    assert storage.files == {}  # файл гостя не остался


def test_without_consent_is_422(client):
    response = upload(client, "cv.pdf", PDF, consent=False)

    assert response.status_code == 422
    assert "нужно согласие" in response.json()["detail"]


def test_wrong_format_is_422(client):
    response = upload(client, "photo.jpg", b"\xff\xd8\xff" + b"\x00" * 10)

    assert response.status_code == 422
    assert response.json()["detail"] == "Подойдёт файл PDF или DOCX"


def test_scan_gives_failed_status_with_text(client):
    job_id = upload(client, "scan.pdf", b"%PDF-1.7\n" + b"\x00" * 100).json()["job_id"]

    status = client.get(f"/api/profile/resume/{job_id}").json()

    assert status["status"] == "failed"
    assert "Не получилось прочитать PDF" in status["error"]


def test_unknown_job_is_pending(client):
    assert client.get("/api/profile/resume/nope").json() == {"status": "pending"}
