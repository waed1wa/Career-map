"""Поиск навыков в тексте резюме по словарю синонимов из справочника.

Это первый, простой способ разбора (неделя 2): без LLM, быстро и одинаково на одном и том же тексте.
На неделе 3 рядом встанет разбор через LLM, а словарь останется запасным путём, если LLM недоступна
(риск Р-4).
"""

import re
from dataclasses import dataclass

from app.modules.career_map.domain import SkillId
from app.modules.catalog.repository import FileCatalog
from app.modules.catalog.schema import normalize

# Границы слова. Перед навыком не должно быть буквы, цифры или . + #, чтобы git не нашёлся
# в «digital», а js — в «node.js» (для него есть свой синоним). После — буквы, цифры, + и #,
# чтобы js не нашёлся в «json». Точку после разрешаем: навык может стоять в конце предложения.
_BEFORE = r"(?<![\w.+#])"
_AFTER = r"(?![\w+#])"


@dataclass(frozen=True)
class FoundSkill:
    skill: SkillId
    title: str
    matched: str  # как навык был написан в резюме — показываем студенту, чтобы он мог проверить


def _alias_pattern(alias: str) -> str:
    """«сводн* таблиц*» → сводн\\w*\\s+таблиц\\w* — слова через любые пробелы и переносы."""
    words = []
    for word in alias.split():
        stem = word.removesuffix("*")
        words.append(re.escape(stem) + (r"\w*" if word.endswith("*") else ""))
    return r"\s+".join(words)


class SkillFinder:
    def __init__(self, catalog: FileCatalog):
        self._patterns: list[tuple[SkillId, str, re.Pattern[str]]] = []
        for skill in catalog.skills():  # порядок справочника
            if not skill.aliases:
                continue
            # длинные синонимы первыми: «rest api» целиком, а не только «rest»
            aliases = sorted(skill.aliases, key=len, reverse=True)
            union = "|".join(_alias_pattern(a) for a in aliases)
            pattern = re.compile(f"{_BEFORE}(?:{union}){_AFTER}")
            self._patterns.append((SkillId(skill.id), skill.title, pattern))

    def find(self, text: str) -> list[FoundSkill]:
        """Навыки из текста — каждый один раз, в порядке справочника."""
        normalized = normalize(text)
        # lower() почти всегда сохраняет длину строки; если нет — показываем найденное строчными
        source = text if len(normalized) == len(text) else normalized
        found = []
        for skill_id, title, pattern in self._patterns:
            match = pattern.search(normalized)
            if match:
                matched = source[match.start() : match.end()]
                found.append(FoundSkill(skill=skill_id, title=title, matched=matched))
        return found
