"""Точка входа API. Модульный монолит: каждый модуль подключает свой роутер.

Модули совпадают с компонентами уровня 3 C4 (API-приложение).
"""

import redis
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.db import database_is_alive
from app.modules.auth.router import router as auth_router
from app.modules.career_map.router import router as career_map_router
from app.modules.catalog.router import router as catalog_router
from app.modules.profile.router import router as profile_router
from app.modules.projects.router import router as projects_router
from app.modules.survey.router import router as survey_router


def redis_is_alive() -> bool:
    try:
        return bool(redis.Redis.from_url(get_settings().redis_url, socket_timeout=1).ping())
    except Exception:
        return False


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name, version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json"
    )

    @app.get("/api/health", tags=["service"])
    def health() -> dict[str, object]:
        """Проверка для smoke-теста: живы ли API, база и очередь."""
        db_ok = database_is_alive()
        redis_ok = redis_is_alive()
        return {
            "status": "ok" if db_ok and redis_ok else "degraded",
            "database": db_ok,
            "redis": redis_ok,
            "environment": settings.environment,
        }

    for router in (
        auth_router,
        profile_router,
        survey_router,
        career_map_router,
        projects_router,
        catalog_router,
    ):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
