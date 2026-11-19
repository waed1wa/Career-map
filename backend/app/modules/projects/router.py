"""Модуль «Проекты и заявки». Спринт 4: витрина проектов, подача и разбор заявок."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def list_projects() -> None:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Проекты появятся в спринте 4")
