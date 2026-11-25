"""Подсчёт опроса: из ответов получаем профессию и навыки студента.

Логика простая и без LLM: каждый вариант ответа заранее связан с навыками справочника.
Дальше этот результат идёт в построитель карты так же, как навыки из резюме.
"""

from dataclasses import dataclass

from app.modules.career_map.domain import SkillId
from app.modules.survey.questions import QUESTIONS, Question


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
    """Проверяет ответы и считает профессию и навыки."""
    raise NotImplementedError("Подсчёт опроса ещё не написан")
