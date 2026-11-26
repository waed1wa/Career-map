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

    # Ключи LLM — только в .env на стенде, в репозитории их нет. Пустой ключ — провайдер не подключён.
    gigachat_api_key: str = ""  # «ключ авторизации» из личного кабинета Studio
    gigachat_scope: str = "GIGACHAT_API_PERS"  # для физлица; для вуза может быть другой
    gigachat_model: str = "GigaChat"
    gigachat_base_url: str = "https://api.giga.chat/v1"
    gigachat_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_ca_bundle: str = ""  # путь к сертификату НУЦ Минцифры; пусто — системные сертификаты
    yandexgpt_api_key: str = ""
    yandexgpt_folder_id: str = ""
    yandexgpt_model: str = "yandexgpt-lite/latest"
    yandexgpt_url: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    # Какая LLM подключена: "fake" для разработки и тестов, "gigachat" или "yandexgpt" на стенде
    llm_provider: str = "fake"
    llm_timeout_seconds: float = 10.0

    # Вход: ключ подписи токенов (в .env — свой, не короче 32 символов) и срок жизни токена
    secret_key: str = "dev-only-secret-change-me-in-env-file"
    token_ttl_minutes: int = 60 * 24

    # Правила по заявкам (инварианты из архитектуры)
    application_reminder_days: int = 5
    application_deadline_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
