"""Модуль «Профиль». Спринт 2: загрузка резюме в MinIO, разбор навыков в фоне."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def my_profile() -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Профиль появится в спринте 2")
