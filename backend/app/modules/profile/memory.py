"""Хранилище и очередь в памяти — для тестов и запуска без Docker."""

from uuid import uuid4

from app.modules.profile.ports import JobState, JobStatus
from app.modules.profile.resume_file import ResumeFileError
from app.modules.profile.resume_service import parse_stored_resume
from app.modules.profile.skill_finder import SkillFinder


class InMemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.files[key] = data

    def get(self, key: str) -> bytes:
        return self.files[key]

    def delete(self, key: str) -> None:
        self.files.pop(key, None)


class ImmediateQueue:
    """Очередь, которая разбирает сразу при постановке. Поведение то же, что у Celery, только без ожидания."""

    def __init__(self, storage: InMemoryStorage, finder: SkillFinder):
        self._storage = storage
        self._finder = finder
        self._jobs: dict[str, JobStatus] = {}

    def submit(self, key: str, filename: str) -> str:
        job_id = uuid4().hex
        try:
            found = parse_stored_resume(self._storage, self._finder, key, filename)
            self._jobs[job_id] = JobStatus(JobState.DONE, skills=tuple(found))
        except ResumeFileError as error:
            self._jobs[job_id] = JobStatus(JobState.FAILED, error=str(error))
        return job_id

    def status(self, job_id: str) -> JobStatus:
        return self._jobs.get(job_id, JobStatus(JobState.PENDING))
