"""Навыки из резюме через LLM (неделя 3) со сверкой по справочнику.

LLM находит то, что в резюме сказано своими словами («писал серверную часть интернет-магазина»),
а словарь — то, что названо прямо. Ответ LLM никогда не берём на веру: оставляем только id,
которые есть в справочнике (риск Р-3). Если LLM недоступна или ответила не по формату —
работаем только по словарю (риск Р-4, TC-03).
"""

from dataclasses import dataclass, field
from typing import Protocol

from app.modules.catalog.repository import FileCatalog
from app.modules.profile.skill_finder import FoundSkill, SkillFinder

MAX_RESUME_CHARS = 6000  # длинное резюме обрезаем: дальше обычно хобби, а токены платные (Р-5)


class Asker(Protocol):
    """То, что умеет LlmGateway: обезличить текст и спросить провайдеров по очереди."""

    def ask(self, prompt: str) -> str: ...


class LlmAnswerError(ValueError):
    """LLM ответила не списком id."""


@dataclass(frozen=True)
class ReadResult:
    skills: list[FoundSkill]
    method: str  # «llm+dictionary» или «dictionary» — пишем в лог, чтобы видеть, как часто LLM подводит
    dropped: list[str] = field(default_factory=list)  # что LLM придумала сверх справочника


def build_prompt(text: str, catalog: FileCatalog) -> str:
    raise NotImplementedError


def parse_skill_ids(answer: str, known: set[str]) -> tuple[list[str], list[str]]:
    """Возвращает (id из справочника, отброшенные id)."""
    raise NotImplementedError


class SkillReader:
    def __init__(self, catalog: FileCatalog, finder: SkillFinder, llm: Asker | None):
        self._catalog = catalog
        self._finder = finder
        self._llm = llm

    def read(self, text: str) -> ReadResult:
        raise NotImplementedError
