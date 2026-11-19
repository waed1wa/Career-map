"""Роутер модуля «Карьерная карта». Пока демо-карта для гостя — для экрана лендинга (спринт 1)."""

from fastapi import APIRouter

from app.modules.career_map.builder import MapBuilder
from app.modules.career_map.demo_catalog import DemoCatalog
from app.modules.career_map.domain import SkillId

router = APIRouter(prefix="/career-map", tags=["career-map"])


@router.get("/demo")
def demo_map() -> dict[str, object]:
    """Демо-карта для гостя: без регистрации и без резюме (вывод из исследования, ФП-3)."""
    career_map = MapBuilder(DemoCatalog()).build("backend-junior", {SkillId("python"), SkillId("git")})
    return {
        "profession_id": career_map.profession_id,
        "steps_left": career_map.steps_left,
        "steps": [
            {"order": s.order, "skill": s.skill.value, "title": s.title, "status": s.status, "why": s.why}
            for s in career_map.steps
        ],
    }
