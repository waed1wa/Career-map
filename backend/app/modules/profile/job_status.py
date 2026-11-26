"""Как результат фоновой задачи разбора превращается в статус для клиента.

Отдельно от Celery, чтобы правила можно было проверить тестами без очереди.
"""

from app.modules.career_map.domain import SkillId
from app.modules.profile.ports import JobState, JobStatus
from app.modules.profile.skill_finder import FoundSkill

QUEUE_FAILED = "Не получилось разобрать резюме. Попробуйте ещё раз или ответьте на вопросы"


def found_to_dict(found: FoundSkill) -> dict[str, str]:
    return {"id": found.skill.value, "title": found.title, "matched": found.matched, "source": found.source}


def status_from_celery(state: str, result: object) -> JobStatus:
    """state — состояние задачи в Celery, result — что вернула задача parse_resume."""
    if state == "SUCCESS" and isinstance(result, dict):
        if "error" in result:
            return JobStatus(JobState.FAILED, error=str(result["error"]))
        skills = tuple(
            FoundSkill(
                skill=SkillId(s["id"]),
                title=s["title"],
                matched=s["matched"],
                source=s.get("source", "dictionary"),
            )
            for s in result.get("skills", [])
        )
        return JobStatus(JobState.DONE, skills=skills)
    if state in ("SUCCESS", "FAILURE", "REVOKED"):  # SUCCESS с непонятным результатом — тоже сбой
        return JobStatus(JobState.FAILED, error=QUEUE_FAILED)
    return JobStatus(JobState.PENDING)  # PENDING, RECEIVED, STARTED, RETRY
