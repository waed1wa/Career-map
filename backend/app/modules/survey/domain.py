"""Подсчёт опроса: из ответов получаем профессию и навыки студента.

Логика простая и без LLM: каждый вариант ответа заранее связан с навыками справочника.
Дальше этот результат идёт в построитель карты так же, как навыки из резюме.
"""

from dataclasses import dataclass

from app.modules.career_map.domain import SkillId
from app.modules.survey.questions import QUESTIONS, Kind, Question


class SurveyError(ValueError):
    """Ответы не подходят. Текст ошибки показываем студенту как есть."""


@dataclass(frozen=True)
class Answer:
    question_id: str
    option_ids: tuple[str, ...]


@dataclass(frozen=True)
class SurveyResult:
    profession_id: str
    skills: frozenset[SkillId]


def evaluate(answers: list[Answer], questions: tuple[Question, ...] = QUESTIONS) -> SurveyResult:
    """Проверяет ответы и считает профессию и навыки.

    Профессию берём из первого по порядку вопроса, где выбранный вариант её задаёт:
    «Кем хотите работать?», а если там «Пока не знаю» — «Что вам интереснее?».
    """
    by_question = _check_questions(answers, questions)

    skills: set[SkillId] = set()
    profession_id: str | None = None
    for question in questions:
        options = {o.id: o for o in question.options}
        chosen = [options[i] for i in _check_options(question, by_question[question.id])]
        for option in chosen:
            skills.update(SkillId(s) for s in option.skills)
            if profession_id is None and option.profession:
                profession_id = option.profession

    if profession_id is None:
        raise SurveyError("По ответам не получилось выбрать профессию")
    return SurveyResult(profession_id=profession_id, skills=frozenset(skills))


def _check_questions(answers: list[Answer], questions: tuple[Question, ...]) -> dict[str, tuple[str, ...]]:
    known = {q.id for q in questions}
    by_question: dict[str, tuple[str, ...]] = {}
    for a in answers:
        if a.question_id not in known:
            raise SurveyError(f"Нет такого вопроса: {a.question_id}")
        if a.question_id in by_question:
            raise SurveyError(f"На вопрос {a.question_id} ответ дан дважды")
        by_question[a.question_id] = a.option_ids
    for q in questions:
        if q.id not in by_question:
            raise SurveyError(f"Ответьте на вопрос: «{q.text}»")
    return by_question


def _check_options(question: Question, option_ids: tuple[str, ...]) -> tuple[str, ...]:
    options = {o.id: o for o in question.options}
    if not option_ids:
        raise SurveyError(f"Выберите хотя бы один вариант: «{question.text}»")
    if len(set(option_ids)) != len(option_ids):
        twice = next(i for i in option_ids if option_ids.count(i) > 1)
        raise SurveyError(f"Вариант {twice} выбран дважды")
    for i in option_ids:
        if i not in options:
            raise SurveyError(f"В вопросе {question.id} нет варианта {i}")
    if question.kind == Kind.SINGLE and len(option_ids) > 1:
        raise SurveyError(f"В вопросе «{question.text}» можно выбрать только один вариант")
    exclusive = [options[i] for i in option_ids if options[i].exclusive]
    if exclusive and len(option_ids) > 1:
        raise SurveyError(f"«{exclusive[0].text}» нельзя выбрать вместе с другими вариантами")
    return option_ids
