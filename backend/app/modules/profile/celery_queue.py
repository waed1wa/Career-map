"""Очередь разбора на Celery — адаптер порта ParseQueue.

На схеме C4 это контейнеры «Очередь» (Redis) и «Фоновый обработчик» (worker).
"""

from celery.result import AsyncResult

from app.modules.profile.job_status import status_from_celery
from app.modules.profile.ports import JobStatus
from app.worker import celery_app, parse_resume


class CeleryParseQueue:
    def submit(self, key: str, filename: str) -> str:
        return str(parse_resume.delay(key, filename).id)

    def status(self, job_id: str) -> JobStatus:
        result = AsyncResult(job_id, app=celery_app)
        return status_from_celery(result.state, result.result if result.ready() else None)
