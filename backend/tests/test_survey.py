"""Опрос: подсчёт профессии и навыков.

Ответы разбиты на классы эквивалентности (лекция 9): верные ответы, «не знаю», «ничего из этого»,
и по одному тесту на каждый вид неверного ответа.
"""

import pytest

from app.modules.career_map.domain import SkillId
from app.modules.catalog.repository import load_catalog
from app.modules.survey.domain import Answer, SurveyError, evaluate
from app.modules.survey.questions import QUESTIONS, Kind, Option, Question


def answers(**chosen: str | list[str]) -> list[Answer]:
    """Все 6 ответов. По умолчанию — бэкенд и «ничего из этого», нужное переопределяем."""
    full: dict[str, str | list[str]] = {
        "goal": "backend",
        "interest": "server",
        "languages": "none",
        "practice": "none",
        "topics": "none",
        "experience": "none",
    }
    full.update(chosen)
    return [Answer(q, tuple([v] if isinstance(v, str) else v)) for q, v in full.items()]


def skills(*ids: str) -> frozenset[SkillId]:
    return frozenset(SkillId(i) for i in ids)


# ---------- верные ответы ----------


def test_full_answers_give_profession_and_skills():
    result = evaluate(
        answers(languages=["python", "sql"], practice=["git", "linux"], topics=["oop"], experience="team")
    )

    assert result.profession_id == "backend-junior"
    assert result.skills == skills("python", "sql", "git", "linux", "oop", "team-project")


def test_not_sure_takes_profession_from_interest():
    result = evaluate(answers(goal="not-sure", interest="numbers"))

    assert result.profession_id == "data-analyst-junior"


def test_goal_wins_over_interest():
    """Если студент прямо выбрал профессию, второй вопрос её не меняет."""
    result = evaluate(answers(goal="frontend", interest="server"))

    assert result.profession_id == "frontend-junior"


def test_typescript_counts_javascript_too():
    result = evaluate(answers(languages="typescript"))

    assert result.skills == skills("typescript", "javascript")


def test_nothing_everywhere_gives_empty_skills():
    """Новичок без опыта — тоже верный ответ: карта начнётся с самого первого шага."""
    result = evaluate(answers())

    assert result.skills == frozenset()


def test_answer_order_does_not_matter():
    forward = answers(languages=["python", "sql"], practice="git")

    assert evaluate(list(reversed(forward))) == evaluate(forward)


# ---------- неверные ответы: по одному классу на тест ----------


def drop(question_id: str) -> list[Answer]:
    return [a for a in answers() if a.question_id != question_id]


INVALID = {
    "missing_question": (drop("topics"), "Ответьте на вопрос: «Какие темы"),
    "unknown_question": (answers() + [Answer("age", ("20",))], "Нет такого вопроса: age"),
    "question_twice": (answers() + [Answer("goal", ("frontend",))], "На вопрос goal ответ дан дважды"),
    "unknown_option": (answers(languages="kotlin"), "В вопросе languages нет варианта kotlin"),
    "two_options_in_single": (answers(goal=["backend", "frontend"]), "можно выбрать только один"),
    "no_option_chosen": (answers(practice=[]), "Выберите хотя бы один вариант"),
    "nothing_plus_something": (answers(practice=["none", "git"]), "нельзя выбрать вместе с другими"),
    "same_option_twice": (answers(languages=["python", "python"]), "Вариант python выбран дважды"),
}


@pytest.mark.parametrize("case", list(INVALID), ids=list(INVALID))
def test_invalid_answers_are_rejected(case):
    given, message = INVALID[case]

    with pytest.raises(SurveyError, match=message):
        evaluate(given)


# ---------- сами вопросы сходятся со справочником ----------


def test_six_to_eight_questions():
    """Граница из плана: 6–8 вопросов. Больше — студент бросит опрос (ФП-3)."""
    assert 6 <= len(QUESTIONS) <= 8


def test_ids_are_unique():
    assert len({q.id for q in QUESTIONS}) == len(QUESTIONS)
    for q in QUESTIONS:
        assert len({o.id for o in q.options}) == len(q.options), q.id


def test_options_point_to_catalog():
    catalog = load_catalog()
    known_skills = {s.id for s in catalog.skills()}
    known_professions = {p.id for p in catalog.professions()}

    for q in QUESTIONS:
        for o in q.options:
            assert set(o.skills) <= known_skills, f"{q.id}/{o.id}"
            assert o.profession is None or o.profession in known_professions, f"{q.id}/{o.id}"


def test_every_catalog_skill_can_be_marked():
    """Иначе навык, который студент знает, навсегда останется на его карте."""
    reachable = {s for q in QUESTIONS for o in q.options for s in o.skills}

    assert {s.id for s in load_catalog().skills()} <= reachable


def test_every_profession_can_be_chosen_directly():
    goal = next(q for q in QUESTIONS if q.id == "goal")

    assert {o.profession for o in goal.options if o.profession} == {
        p.id for p in load_catalog().professions()
    }


def test_exclusive_options_only_in_multi_questions():
    for q in QUESTIONS:
        if any(o.exclusive for o in q.options):
            assert q.kind == Kind.MULTI, q.id


def test_no_profession_in_answers_is_reported():
    """Защита на будущее: если вопросы поменяют и профессия не выберется, ответим ошибкой, а не картой."""
    one = (Question("q", "Вопрос", Kind.SINGLE, (Option("a", "Вариант", skills=("git",)),)),)

    with pytest.raises(SurveyError, match="не получилось выбрать профессию"):
        evaluate([Answer("q", ("a",))], one)
