"""Модуль «Справочник»: профессии, навыки, материалы. Спринт 3 — наполнение (60 навыков)."""

from fastapi import APIRouter

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/professions")
def professions() -> list[dict[str, str]]:
    """Пока одна профессия из демо-справочника."""
    return [{"id": "backend-junior", "title": "Junior Backend-разработчик"}]
