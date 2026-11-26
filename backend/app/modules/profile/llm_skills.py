"""Навыки из резюме через LLM (неделя 3) со сверкой по справочнику.

LLM находит то, что в резюме сказано своими словами («писал серверную часть интернет-магазина»),
а словарь — то, что названо прямо. Ответ LLM никогда не берём на веру: оставляем только id,
которые есть в справочнике (риск Р-3). Если LLM недоступна или ответила не по формату —
работаем только по словарю (риск Р-4, TC-03).
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Protocol

from app.modules.career_map.domain import SkillId
from app.modules.catalog.repository import FileCatalog
from app.modules.profile.skill_finder import FoundSkill, SkillFinder

log = logging.getLogger(__name__)

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


_PROMPT = """Ты помогаешь разобрать резюме студента. Ниже список навыков и текст резюме.
Выбери навыки из списка, которые у студента точно есть: он ими пользовался в учёбе, проекте или работе.
Навыки, о которых сказано «не работал» или «хочу изучить», не выбирай.
Ответь только JSON-массивом id из списка, без пояснений. Например: ["python", "git"].
Если ничего не подходит, ответь [].

Навыки:
{skills}

Резюме:
\"\"\"
{resume}
\"\"\"
"""

_ARRAY = re.compile(r"\[[^\[\]]*\]", re.DOTALL)  # первый [...] в ответе, даже если вокруг текст


def build_prompt(text: str, catalog: FileCatalog) -> str:
    skills = "\n".join(f"- {s.id}: {s.title}" for s in catalog.skills())
    return _PROMPT.format(skills=skills, resume=text[:MAX_RESUME_CHARS])


def parse_skill_ids(answer: str, known: set[str]) -> tuple[list[str], list[str]]:
    """Возвращает (id из справочника, отброшенные id). Всё, что не список строк, — LlmAnswerError."""
    match = _ARRAY.search(answer)
    if not match:
        raise LlmAnswerError("В ответе нет JSON-массива")
    try:
        items = json.loads(match.group())
    except json.JSONDecodeError as error:
        raise LlmAnswerError("Массив в ответе — не JSON") from error
    if not all(isinstance(i, str) for i in items):
        raise LlmAnswerError("В массиве не только строки")
    kept: list[str] = []
    dropped: list[str] = []
    for item in items:
        skill_id = item.strip().lower()
        target = kept if skill_id in known else dropped
        if skill_id not in target:
            target.append(skill_id)
    return kept, dropped


class SkillReader:
    def __init__(self, catalog: FileCatalog, finder: SkillFinder, llm: Asker | None):
        self._catalog = catalog
        self._finder = finder
        self._llm = llm

    def find(self, text: str) -> list[FoundSkill]:
        """То же, что у SkillFinder, — чтобы фоновая задача не знала, какой способ работает."""
        result = self.read(text)
        log.info("Навыки из резюме: способ %s, найдено %d", result.method, len(result.skills))
        return result.skills

    def read(self, text: str) -> ReadResult:
        by_dictionary = {f.skill.value: f for f in self._finder.find(text)}
        if self._llm is None:
            return ReadResult(list(by_dictionary.values()), "dictionary")
        try:
            answer = self._llm.ask(build_prompt(text, self._catalog))
            by_llm, dropped = parse_skill_ids(answer, {s.id for s in self._catalog.skills()})
        except Exception as error:  # LLM молчит или ответила не по формату — хватит и словаря
            log.warning("Навыки из резюме только по словарю: %s", error)
            return ReadResult(list(by_dictionary.values()), "dictionary")
        if dropped:
            log.info("LLM назвала навыки не из справочника, отбросили: %s", dropped)

        found = []
        for skill in self._catalog.skills():  # порядок справочника, как у словаря
            if skill.id in by_dictionary:
                found.append(by_dictionary[skill.id])
            elif skill.id in by_llm:
                found.append(FoundSkill(SkillId(skill.id), skill.title, matched="", source="llm"))
        return ReadResult(found, "llm+dictionary", dropped)
