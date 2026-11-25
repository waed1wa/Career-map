"""Формат файла справочника и проверка его целостности.

Справочник правят руками, поэтому ошибки в нём ловим при загрузке, а не на экране у студента:
повтор id, ссылка на несуществующий навык, цикл в порядке изучения, слишком короткая профессия.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.career_map.builder import MIN_STEPS

_ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
# Слово синонима: буквы, цифры и . + # / - внутри; «*» в конце — «любое окончание» (питон* → питоне)
_ALIAS_WORD = re.compile(r"^[\w.+#/-]+\*?$")
MIN_STEM = 3  # «ру*» нашло бы и «русский», и «руководитель» — слишком коротко


def normalize(text: str) -> str:
    """Как сравниваем текст со словарём: без регистра и без «ё»."""
    return text.lower().replace("ё", "е")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SkillData(_Frozen):
    id: str = Field(pattern=_ID.pattern)
    title: str = Field(min_length=1)
    why: str = Field(min_length=1)  # «зачем этот шаг» — без него студент не понимает, зачем учить
    prerequisites: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)  # как навык пишут в резюме: «postgresql» → sql

    @model_validator(mode="after")
    def _check_aliases(self) -> "SkillData":
        for alias in self.aliases:
            if alias != normalize(alias).strip() or not alias:
                raise ValueError(
                    f"Навык {self.id}: синоним «{alias}» пишем строчными, без «ё» и пробелов по краям"
                )
            for word in alias.split():
                if not _ALIAS_WORD.match(word):
                    raise ValueError(f"Навык {self.id}: в синониме «{alias}» недопустимые символы")
                if word.endswith("*") and len(word) - 1 < MIN_STEM:
                    raise ValueError(f"Навык {self.id}: в синониме «{alias}» слишком короткая основа")
        return self


class ProfessionData(_Frozen):
    id: str = Field(pattern=_ID.pattern)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    skills: list[str]  # порядок в списке = рекомендуемый порядок изучения
    why_overrides: dict[str, str] = Field(default_factory=dict)


class CatalogData(_Frozen):
    version: int
    skills: list[SkillData]
    professions: list[ProfessionData]

    @model_validator(mode="after")
    def _check(self) -> "CatalogData":
        skill_ids = [s.id for s in self.skills]
        _no_duplicates(skill_ids, "навык")
        _no_duplicates([p.id for p in self.professions], "профессия")
        _no_duplicates([a for s in self.skills for a in s.aliases], "синоним")
        known = set(skill_ids)

        for s in self.skills:
            for pre in s.prerequisites:
                if pre not in known:
                    raise ValueError(f"Навык {s.id}: в порядке изучения неизвестный навык {pre}")
        _no_cycles({s.id: s.prerequisites for s in self.skills})

        prereq = {s.id: set(s.prerequisites) for s in self.skills}
        for p in self.professions:
            _no_duplicates(p.skills, f"навык в профессии {p.id}")
            for skill_id in [*p.skills, *p.why_overrides]:
                if skill_id not in known:
                    raise ValueError(f"Профессия {p.id}: неизвестный навык {skill_id}")
            if len(p.skills) < MIN_STEPS:
                raise ValueError(
                    f"Профессия {p.id}: {len(p.skills)} навыков, а на карте должно быть не меньше {MIN_STEPS}"
                )
            seen: set[str] = set()
            for skill_id in p.skills:
                late = (prereq[skill_id] & set(p.skills)) - seen
                if late:
                    raise ValueError(
                        f"Профессия {p.id}: {skill_id} стоит раньше, чем {', '.join(sorted(late))}"
                    )
                seen.add(skill_id)
        return self


def _no_duplicates(ids: list[str], what: str) -> None:
    seen: set[str] = set()
    for i in ids:
        if i in seen:
            raise ValueError(f"Повторяется {what}: {i}")
        seen.add(i)


def _no_cycles(graph: dict[str, list[str]]) -> None:
    done: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> None:
        if node in done:
            return
        if node in path:
            cycle = [*path[path.index(node) :], node]
            raise ValueError(f"Цикл в порядке изучения: {' → '.join(cycle)}")
        path.append(node)
        for pre in graph.get(node, []):
            visit(pre)
        path.pop()
        done.add(node)

    for node in graph:
        visit(node)
