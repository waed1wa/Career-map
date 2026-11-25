"""Модуль «Профиль»: загрузка резюме и разбор навыков в фоне (неделя 2).

Клиент загружает файл и сразу получает номер задачи, а потом раз в 2 секунды спрашивает статус —
так API не ждёт разбора (на неделе 3 его будет делать LLM, это дольше).
Пока входа нет, резюме разбирается для гостя и файл удаляется сразу после разбора.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.modules.profile.job_status import found_to_dict
from app.modules.profile.minio_storage import MinioResumeStorage
from app.modules.profile.resume_file import ResumeFileError, check_resume_file
from app.modules.profile.resume_service import ResumeService

router = APIRouter(prefix="/profile", tags=["profile"])


@lru_cache
def get_resume_service() -> ResumeService:
    from app.modules.profile.celery_queue import CeleryParseQueue  # Celery нужен только здесь

    return ResumeService(MinioResumeStorage.from_settings(get_settings()), CeleryParseQueue())


Service = Annotated[ResumeService, Depends(get_resume_service)]


@router.get("/me", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def my_profile() -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Профиль появится вместе со входом")


@router.post("/resume", status_code=status.HTTP_202_ACCEPTED)
def upload_resume(
    service: Service,
    file: Annotated[UploadFile, File(description="PDF или DOCX до 5 МБ")],
    consent: Annotated[bool, Form(description="Согласие на обработку данных резюме")] = False,
) -> dict[str, str]:
    """Принимает резюме и ставит разбор в очередь. Ответ — номер задачи для опроса статуса."""
    filename = file.filename or ""
    try:
        if file.size is not None:  # огромный файл отсекаем, не читая его в память
            check_resume_file(filename, file.size)
        job_id = service.upload(filename, file.file.read(), consent)
    except ResumeFileError as error:
        raise HTTPException(422, str(error)) from None
    return {"job_id": job_id}


@router.get("/resume/{job_id}")
def resume_status(job_id: str, service: Service) -> dict[str, object]:
    """pending — ещё разбираем; done — навыки готовы; failed — текст ошибки для студента."""
    job = service.status(job_id)
    answer: dict[str, object] = {"status": job.state.value}
    if job.state == "done":
        answer["skills"] = [found_to_dict(s) for s in job.skills]
    if job.error:
        answer["error"] = job.error
    return answer
