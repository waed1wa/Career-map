"""Поиск навыков в тексте резюме по словарю синонимов из справочника.

Это первый, простой способ разбора (неделя 2): без LLM, быстро и одинаково на одном и том же тексте.
На неделе 3 рядом встанет разбор через LLM, а словарь останется запасным путём, если LLM недоступна
(риск Р-4).
"""

from dataclasses import dataclass

from app.modules.career_map.domain import SkillId
from app.modules.catalog.repository import FileCatalog


@dataclass(frozen=True)
class FoundSkill:
    skill: SkillId
    title: str
    matched: str  # как навык был написан в резюме — показываем студенту, чтобы он мог проверить


class SkillFinder:
    def __init__(self, catalog: FileCatalog):
        self._catalog = catalog

    def find(self, text: str) -> list[FoundSkill]:
        """Навыки из текста — каждый один раз, в порядке справочника."""
        raise NotImplementedError("Поиск по словарю ещё не написан")
