"""Фоновый обработчик и планировщик (контейнеры worker и beat на схеме C4 уровня 2).

Это тот же код, что и API, только запущенный другой командой:
    celery -A app.worker worker   — фоновый обработчик
    celery -A app.worker beat     — планировщик
"""

import logging

from celery import Celery

from app.core.config import get_settings
from app.integrations.llm.gateway import build_gateway
from app.modules.career_map.builder import MapBuilder
from app.modules.career_map.demo_catalog import DemoCatalog
from app.modules.career_map.domain import SkillId
from app.modules.catalog.repository import get_catalog
from app.modules.profile.job_status import found_to_dict
from app.modules.profile.llm_skills import SkillReader
from app.modules.profile.minio_storage import MinioResumeStorage
from app.modules.profile.resume_file import ResumeFileError
from app.modules.profile.resume_service import parse_stored_resume
from app.modules.profile.skill_finder import SkillFinder

log = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery("karernaya_karta", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    timezone="Europe/Moscow",
    task_acks_late=True,
    beat_schedule={
        "check-application-deadlines": {"task": "app.worker.check_deadlines", "schedule": 3600.0},
    },
)


@celery_app.task(name="app.worker.build_map")
def build_map(profession_id: str, skills: list[str]) -> dict[str, object]:
    """Строит карту в фоне, чтобы API не ждал LLM (НФТ: карта за 30 секунд)."""
    builder = MapBuilder(DemoCatalog(), build_gateway())
    career_map = builder.build(profession_id, {SkillId(s) for s in skills})
    return {"profession_id": career_map.profession_id, "steps": [s.skill.value for s in career_map.steps]}


@celery_app.task(name="app.worker.parse_resume")
def parse_resume(key: str, filename: str) -> dict[str, object]:
    """Разбор резюме: LLM со сверкой по справочнику, а если LLM недоступна — словарь.

    Файл удаляется из MinIO сразу после разбора.

    Ошибку в файле (скан, повреждён) возвращаем как результат, а не как сбой задачи:
    её текст нужно показать студенту.
    """
    storage = MinioResumeStorage.from_settings(settings)
    try:
        catalog = get_catalog()
        reader = SkillReader(catalog, SkillFinder(catalog), build_gateway())
        found = parse_stored_resume(storage, reader, key, filename)
    except ResumeFileError as error:
        return {"error": str(error)}
    return {"skills": [found_to_dict(f) for f in found]}


@celery_app.task(name="app.worker.check_deadlines")
def check_deadlines() -> int:
    """Раз в час: напоминания на 5-й день и «просрочена» на 7-й. Работу с базой добавим в спринте 4."""
    log.info("Проверка сроков заявок (пока без базы)")
    return 0
