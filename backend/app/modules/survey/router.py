"""Модуль «Опрос». Спринт 2: 6–8 вопросов вместо резюме (для тех, у кого его нет)."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/survey", tags=["survey"])


@router.get("/questions", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def questions() -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Опрос появится в спринте 2")
