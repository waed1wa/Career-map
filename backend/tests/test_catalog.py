"""Справочник: целостность данных и работа как источник для построителя карты.

Битые справочники разбиты по классам эквивалентности (лекция 9): у каждого теста одна ошибка,
и проверяем, что загрузка её находит и называет понятным текстом.
"""

import copy
import json

import pytest
from pydantic import ValidationError

from app.modules.career_map.builder import MAX_STEPS, MIN_STEPS, MapBuilder
from app.modules.career_map.domain import SkillId, StepStatus
from app.modules.catalog.repository import (
    CATALOG_FILE,
    FileCatalog,
    UnknownProfessionError,
    get_catalog,
    load_catalog,
)
from app.modules.catalog.schema import CatalogData

PROFESSIONS = ["backend-junior", "frontend-junior", "data-analyst-junior"]


# ---------- настоящий справочник ----------


def test_real_catalog_loads():
    catalog = load_catalog()

    assert [p.id for p in catalog.professions()] == PROFESSIONS
    assert len(catalog.skills()) == 20


def test_every_skill_is_used_by_some_profession():
    """Навык, которого нет ни в одной профессии, никогда не попадёт на карту — значит, лишний."""
    catalog = load_catalog()
    used = {s for p in catalog.professions() for s in p.skills}

    assert {s.id for s in catalog.skills()} == used


@pytest.mark.parametrize("profession_id", PROFESSIONS)
def test_map_for_every_profession(profession_id):
    """Для каждой профессии из справочника строится карта 6–8 шагов с одним текущим шагом."""
    career_map = MapBuilder(load_catalog()).build(profession_id, set())

    assert MIN_STEPS <= len(career_map.steps) <= MAX_STEPS
    assert sum(1 for s in career_map.steps if s.status == StepStatus.CURRENT) == 1
    assert all(s.why for s in career_map.steps)


@pytest.mark.parametrize("profession_id", PROFESSIONS)
def test_beginner_map_follows_catalog_order(profession_id):
    """Новичку показываем первые 8 навыков профессии ровно в том порядке, что в справочнике."""
    catalog = load_catalog()
    expected = catalog.profession(profession_id).skills[:MAX_STEPS]

    career_map = MapBuilder(catalog).build(profession_id, set())

    assert [s.skill.value for s in career_map.steps] == expected


def test_every_skill_except_resume_has_aliases():
    """Без синонимов навык нельзя найти в резюме. «Резюме и отклики» в тексте резюме не ищем."""
    without = {s.id for s in load_catalog().skills() if not s.aliases}

    assert without == {"resume"}


def test_why_can_differ_by_profession():
    catalog = load_catalog()
    backend = {s.skill.value: s.why for s in catalog.required_skills("backend-junior")}
    analyst = {s.skill.value: s.why for s in catalog.required_skills("data-analyst-junior")}

    assert backend["python"] != analyst["python"]
    assert backend["sql"] == analyst["sql"]  # без особого пояснения берётся общее


def test_unknown_profession():
    with pytest.raises(UnknownProfessionError):
        load_catalog().required_skills("devops-senior")


def test_catalog_is_read_once():
    assert get_catalog() is get_catalog()


# ---------- битый справочник: одна ошибка на тест ----------


def base() -> dict:
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


def skill(data: dict, skill_id: str) -> dict:
    return next(s for s in data["skills"] if s["id"] == skill_id)


def break_catalog(change) -> dict:
    data = copy.deepcopy(base())
    change(data)
    return data


BROKEN = {
    "duplicate_skill": (
        lambda d: d["skills"].append(dict(skill(d, "git"))),
        "Повторяется навык: git",
    ),
    "unknown_prerequisite": (
        lambda d: skill(d, "react")["prerequisites"].append("vue"),
        "неизвестный навык vue",
    ),
    "cycle": (
        lambda d: skill(d, "python")["prerequisites"].append("oop"),
        "Цикл в порядке изучения",
    ),
    "profession_unknown_skill": (
        lambda d: d["professions"][0]["skills"].append("kotlin"),
        "Профессия backend-junior: неизвестный навык kotlin",
    ),
    "wrong_order_in_profession": (
        lambda d: d["professions"][0]["skills"].reverse(),
        "стоит раньше, чем",
    ),
    "empty_why": (
        lambda d: skill(d, "sql").update(why=""),
        "at least 1 character",
    ),
    "bad_id": (
        lambda d: skill(d, "git").update(id="Git Hub"),
        "should match pattern",
    ),
    "same_alias_for_two_skills": (
        lambda d: skill(d, "pandas")["aliases"].append("python"),
        "Повторяется синоним: python",
    ),
    "alias_in_upper_case": (
        lambda d: skill(d, "git")["aliases"].append("GitHub Actions"),
        "пишем строчными",
    ),
    "alias_stem_too_short": (
        lambda d: skill(d, "sql")["aliases"].append("бд*"),
        "слишком короткая основа",
    ),
    "alias_with_bad_symbols": (
        lambda d: skill(d, "sql")["aliases"].append("sql;drop"),
        "недопустимые символы",
    ),
    "duplicate_skill_in_profession": (
        lambda d: d["professions"][1]["skills"].append("git"),
        "Повторяется навык в профессии frontend-junior: git",
    ),
}


@pytest.mark.parametrize("case", list(BROKEN), ids=list(BROKEN))
def test_broken_catalog_is_rejected(case):
    change, message = BROKEN[case]

    with pytest.raises(ValidationError, match=message):
        CatalogData.model_validate(break_catalog(change))


def _with_backend_skills(count: int) -> dict:
    def change(d: dict) -> None:
        d["professions"][0]["skills"] = d["professions"][0]["skills"][:count]

    return break_catalog(change)


def test_profession_with_min_steps_is_ok():
    """Граница: ровно MIN_STEPS навыков — можно."""
    CatalogData.model_validate(_with_backend_skills(MIN_STEPS))


def test_profession_with_fewer_than_min_steps_is_rejected():
    """Граница: на один навык меньше — нельзя, карта получится короче 6 шагов."""
    with pytest.raises(ValidationError, match=f"не меньше {MIN_STEPS}"):
        CatalogData.model_validate(_with_backend_skills(MIN_STEPS - 1))


def test_file_catalog_works_with_custom_data():
    catalog = FileCatalog(CatalogData.model_validate(base()))

    assert SkillId("javascript") in catalog.prerequisites()[SkillId("react")]
    assert catalog.skill("sql") is not None
    assert catalog.skill("cobol") is None
