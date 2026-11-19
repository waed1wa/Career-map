"""Настройки приложения. Всё берётся из переменных окружения (см. .env.example)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Карьерная карта"
    environment: str = "local"

    database_url: str = "postgresql+psycopg://kk:kk@localhost:5432/kk"
    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "kk-minio"
    minio_secret_key: str = "kk-minio-secret"
    minio_bucket_resumes: str = "resumes"

    # Какая LLM подключена: "fake" для разработки и тестов, "gigachat" или "yandexgpt" на стенде
    llm_provider: str = "fake"
    llm_timeout_seconds: float = 10.0

    # Правила по заявкам (инварианты из архитектуры)
    application_reminder_days: int = 5
    application_deadline_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
