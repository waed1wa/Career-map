"""Модуль «Опрос»: 6 вопросов вместо резюме, для тех, у кого его нет (ФП-3).

Без входа: гость проходит опрос и сразу видит свои навыки, а регистрация нужна только чтобы
сохранить результат. Сохранение ответов в таблицу подключим, когда в main появится вход
(пулл-реквест Моисеенко), — без него не к кому привязать ответы.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.modules.catalog.repository import FileCatalog, get_catalog
from app.modules.survey.domain import Answer, SurveyError, evaluate
from app.modules.survey.questions import QUESTIONS

router = APIRouter(prefix="/survey", tags=["survey"])

Catalog = Annotated[FileCatalog, Depends(get_catalog)]


class AnswerIn(BaseModel):
    question_id: str = Field(max_length=50)
    option_ids: list[str] = Field(max_length=20)


class SurveyIn(BaseModel):
    answers: list[AnswerIn] = Field(max_length=20)


@router.get("/questions")
def questions() -> list[dict[str, object]]:
    """Вопросы и варианты. Какие навыки стоят за вариантом, клиенту не отдаём — это логика сервера."""
    return [
        {
            "id": q.id,
            "text": q.text,
            "kind": q.kind.value,
            "options": [{"id": o.id, "text": o.text, "exclusive": o.exclusive} for o in q.options],
        }
        for q in QUESTIONS
    ]


@router.post("/result")
def result(body: SurveyIn, catalog: Catalog) -> dict[str, object]:
    """Профессия и навыки по ответам. Ошибка в ответах — 422 с понятным текстом."""
    try:
        outcome = evaluate([Answer(a.question_id, tuple(a.option_ids)) for a in body.answers])
    except SurveyError as error:
        raise HTTPException(422, str(error)) from None

    profession = catalog.profession(outcome.profession_id)
    known = {s.value for s in outcome.skills}
    return {
        "profession": {"id": profession.id, "title": profession.title},
        # в порядке справочника, чтобы список на экране не прыгал от запроса к запросу
        "skills": [{"id": s.id, "title": s.title} for s in catalog.skills() if s.id in known],
    }
