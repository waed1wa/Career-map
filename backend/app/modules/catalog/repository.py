"""Справочник из файла catalog.json — адаптер порта CatalogRepository (гексагональная схема).

На неделе 4 рядом появится SqlCatalogRepository с тем же интерфейсом, а этот файл станет
начальными данными для базы. Построитель карты разницы не заметит.
"""

from functools import lru_cache
from pathlib import Path

from app.modules.career_map.domain import RequiredSkill, SkillId
from app.modules.catalog.schema import CatalogData, ProfessionData, SkillData

CATALOG_FILE = Path(__file__).parent / "data" / "catalog.json"


class UnknownProfessionError(KeyError):
    """Такой профессии нет в справочнике."""


class FileCatalog:
    def __init__(self, data: CatalogData):
        self._data = data
        self._skills = {s.id: s for s in data.skills}
        self._professions = {p.id: p for p in data.professions}

    # --- порт CatalogRepository (им пользуется построитель карты) ---

    def required_skills(self, profession_id: str) -> list[RequiredSkill]:
        """Навыки профессии в рекомендуемом порядке изучения."""
        profession = self.profession(profession_id)
        return [
            RequiredSkill(
                skill=SkillId(skill_id),
                title=self._skills[skill_id].title,
                why=profession.why_overrides.get(skill_id, self._skills[skill_id].why),
            )
            for skill_id in profession.skills
        ]

    def prerequisites(self) -> dict[SkillId, set[SkillId]]:
        return {
            SkillId(s.id): {SkillId(p) for p in s.prerequisites} for s in self._data.skills if s.prerequisites
        }

    # --- чтение для API и других модулей (опрос, разбор резюме) ---

    def professions(self) -> list[ProfessionData]:
        return list(self._data.professions)

    def profession(self, profession_id: str) -> ProfessionData:
        try:
            return self._professions[profession_id]
        except KeyError:
            raise UnknownProfessionError(profession_id) from None

    def skills(self) -> list[SkillData]:
        return list(self._data.skills)

    def skill(self, skill_id: str) -> SkillData | None:
        return self._skills.get(skill_id)


def load_catalog(path: Path = CATALOG_FILE) -> FileCatalog:
    """Читает и проверяет файл. Ошибка в справочнике — ValidationError с понятным текстом."""
    return FileCatalog(CatalogData.model_validate_json(path.read_text(encoding="utf-8")))


@lru_cache
def get_catalog() -> FileCatalog:
    """Один справочник на всё приложение: файл читается один раз."""
    return load_catalog()
