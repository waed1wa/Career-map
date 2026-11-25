"""Модуль «Справочник»: профессии и навыки.

Только чтение и без входа: справочник нужен гостю на лендинге и на экране «Список навыков»
(третий способ входа, ФП-3). Материалы к навыкам появятся на неделе 4.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.catalog.repository import FileCatalog, UnknownProfessionError, get_catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])

# Справочник приходит через зависимость FastAPI: в тестах его можно подменить
Catalog = Annotated[FileCatalog, Depends(get_catalog)]


@router.get("/professions")
def professions(catalog: Catalog) -> list[dict[str, object]]:
    """Профессии, для которых можно построить карту."""
    return [
        {"id": p.id, "title": p.title, "description": p.description, "skills_count": len(p.skills)}
        for p in catalog.professions()
    ]


@router.get("/professions/{profession_id}")
def profession(profession_id: str, catalog: Catalog) -> dict[str, object]:
    """Профессия и её навыки в рекомендуемом порядке изучения."""
    try:
        p = catalog.profession(profession_id)
    except UnknownProfessionError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Такой профессии нет в справочнике") from None
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "skills": [
            {"id": s.skill.value, "title": s.title, "why": s.why} for s in catalog.required_skills(p.id)
        ],
    }


@router.get("/skills")
def skills(catalog: Catalog) -> list[dict[str, object]]:
    """Все навыки — для экрана, где студент сам отмечает, что уже умеет."""
    return [{"id": s.id, "title": s.title, "why": s.why} for s in catalog.skills()]
