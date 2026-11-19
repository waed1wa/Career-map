"""Модуль «Вход и роли». Неделя 1: регистрация, вход по токену, роли студент и организатор."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def me() -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Вход появится на неделе 1")
