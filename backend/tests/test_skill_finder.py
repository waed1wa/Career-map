"""Поиск навыков в резюме по словарю.

Классы эквивалентности (лекция 9): точное название, другой регистр, синоним, русское окончание,
навык внутри другого слова (не должен находиться), спецсимволы, пустой текст.
"""

import pytest

from app.modules.catalog.repository import load_catalog
from app.modules.profile.skill_finder import SkillFinder

finder = SkillFinder(load_catalog())


def ids(text: str) -> list[str]:
    return [f.skill.value for f in finder.find(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Python, Git", ["git", "python"]),
        ("PYTHON и GIT", ["git", "python"]),
        ("Базы данных: PostgreSQL, MySQL", ["sql"]),
        ("Делал бэкенд на Django", ["web-framework"]),
        ("Опыт работы с питоном полгода", ["python"]),
        ("Строил отчёты со сводными таблицами", ["excel"]),
        ("Уверенно работаю в командной\nстроке", ["linux"]),
        ("Вёрстка лендингов", ["html-css"]),
        ("Знаю ООП и паттерны", ["oop"]),
        ("Node.js, React.js", ["javascript", "react"]),
        ("HTML/CSS", ["html-css"]),
        ("Писал REST API на FastAPI", ["http-api", "web-framework"]),
        ("Стажёр junior-python", ["python"]),
    ],
    ids=[
        "exact",
        "upper_case",
        "synonyms",
        "framework",
        "russian_ending",
        "russian_two_words",
        "line_break_between_words",
        "yo_letter",
        "russian_abbreviation",
        "dot_inside_name",
        "slash_between_skills",
        "api_and_fastapi",
        "after_hyphen",
    ],
)
def test_skills_are_found(text, expected):
    assert ids(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Digital-маркетинг",  # git внутри слова
        "Excellent communication skills",  # excel внутри слова
        "Работал в ресторане, restaurant manager",  # rest внутри слова
        "Писал на Java и C++",  # Java — не JavaScript, C++ нет в справочнике
        "Формат JSON",  # js внутри слова
        "Реакция на замечания",  # «реакт» — только целым словом
    ],
    ids=["git_in_word", "excel_in_word", "rest_in_word", "java_is_not_js", "js_in_json", "react_in_word"],
)
def test_no_false_matches(text):
    assert ids(text) == []


def test_empty_text():
    assert finder.find("") == []


def test_each_skill_once_in_catalog_order():
    """Порядок не зависит от того, как навыки стоят в резюме, — список на экране не прыгает."""
    text = "Docker, Python, Git, снова Python и python3"

    assert ids(text) == ["git", "python", "docker"]


def test_matched_shows_how_it_was_written():
    found = finder.find("СУБД: PostgreSQL")

    assert [(f.skill.value, f.matched, f.title) for f in found] == [
        ("sql", "PostgreSQL", "SQL и базы данных"),
    ]


def test_resume_skill_is_never_found():
    """«Резюме и отклики» — это не то, что пишут в резюме, а то, что студент делает с ним."""
    assert "resume" not in ids("Моё резюме: отклики на стажировки")
