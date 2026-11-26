"""Загрузка резюме и разбор в фоне (неделя 2): файл → MinIO → очередь → навыки.

Пока нет входа, резюме загружает гость. Такой файл не храним: он лежит в MinIO, только пока
его разбирает фоновая задача, и удаляется сразу после разбора — даже если разбор упал
(152-ФЗ, риск Р-8). Когда появится вход, навыки будем сохранять в профиль студента.
"""

from uuid import uuid4

from app.modules.profile.ports import JobStatus, ParseQueue, ResumeStorage
from app.modules.profile.resume_file import ResumeFileError, check_resume_file, extract_text
from app.modules.profile.skill_finder import FoundSkill, SkillFinder

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class ResumeService:
    def __init__(self, storage: ResumeStorage, queue: ParseQueue):
        self._storage = storage
        self._queue = queue

    def upload(self, filename: str, data: bytes, consent: bool) -> str:
        """Проверяет файл, кладёт в хранилище и ставит разбор в очередь. Возвращает номер задачи."""
        if not consent:
            raise ResumeFileError("Чтобы разобрать резюме, нужно согласие на обработку данных")
        extension = check_resume_file(filename, len(data))  # плохой файл даже не сохраняем
        key = f"guest/{uuid4().hex}.{extension}"  # имя файла студента в ключ не попадает
        self._storage.put(key, data, CONTENT_TYPES[extension])
        return self._queue.submit(key, filename)

    def status(self, job_id: str) -> JobStatus:
        return self._queue.status(job_id)


def parse_stored_resume(
    storage: ResumeStorage, finder: SkillFinder, key: str, filename: str
) -> list[FoundSkill]:
    """Это и делает фоновая задача. Файл удаляется в любом случае."""
    try:
        return finder.find(extract_text(filename, storage.get(key)))
    finally:
        storage.delete(key)
