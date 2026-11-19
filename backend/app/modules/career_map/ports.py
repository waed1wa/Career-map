"""Порты (интерфейсы) модуля карты. Реализации-адаптеры подключаются при запуске."""

from typing import Protocol

from app.modules.career_map.domain import CareerMap, RequiredSkill, SkillId


class CatalogRepository(Protocol):
    """Справочник: что нужно для профессии и в каком порядке это учить."""

    def required_skills(self, profession_id: str) -> list[RequiredSkill]: ...

    def prerequisites(self) -> dict[SkillId, set[SkillId]]: ...


class Explainer(Protocol):
    """Пишет пояснения «почему этот шаг». Шаги не выбирает — только текст."""

    def explain(self, career_map: CareerMap) -> dict[SkillId, str]: ...


class MapRepository(Protocol):
    def save(self, user_id: str, career_map: CareerMap) -> None: ...
