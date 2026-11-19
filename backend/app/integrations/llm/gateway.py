"""LLM-шлюз — адаптер для порта Explainer.

Правила из архитектуры:
- в LLM уходит только обезличенный текст (ПДн не покидают наш сервер, 152-ФЗ);
- LLM пишет пояснения, но не выбирает шаги и материалы;
- если основной провайдер не ответил — пробуем запасной, если и он молчит — карта без пояснений.
"""

import logging
import re
from typing import Protocol

from app.modules.career_map.domain import CareerMap, SkillId

log = logging.getLogger(__name__)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
_URL = re.compile(r"(?:https?://|www\.|t\.me/|vk\.com/)\S+", re.IGNORECASE)


def anonymize(text: str) -> str:
    """Убирает почту, телефоны и ссылки на профили до отправки в LLM (тест TC-04)."""
    text = _EMAIL.sub("[почта]", text)
    text = _URL.sub("[ссылка]", text)
    return _PHONE.sub("[телефон]", text)


class LlmClient(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


class LlmUnavailable(Exception):
    pass


class FakeLlmClient:
    """Для тестов и локальной разработки: отвечает сразу и одинаково."""

    name = "fake"

    def complete(self, prompt: str) -> str:
        return "Этот шаг нужен, чтобы закрыть требование из вакансий."


class GigaChatClient:
    """Заглушка. Подключение к API — спринт 3 (нужен ключ в .env)."""

    name = "gigachat"

    def complete(self, prompt: str) -> str:
        raise LlmUnavailable("GigaChat ещё не подключён")


class YandexGptClient:
    """Запасной провайдер. Подключение — спринт 3."""

    name = "yandexgpt"

    def complete(self, prompt: str) -> str:
        raise LlmUnavailable("YandexGPT ещё не подключён")


class LlmGateway:
    """Перебирает провайдеров по очереди. Реализует порт Explainer."""

    def __init__(self, clients: list[LlmClient]):
        self._clients = clients

    def ask(self, prompt: str) -> str:
        safe_prompt = anonymize(prompt)
        for client in self._clients:
            try:
                return client.complete(safe_prompt)
            except Exception as exc:
                log.warning("LLM %s не ответила: %s", client.name, exc)
        raise LlmUnavailable("Ни один провайдер не ответил")

    def explain(self, career_map: CareerMap) -> dict[SkillId, str]:
        result: dict[SkillId, str] = {}
        for step in career_map.steps:
            prompt = f"Объясни студенту в 1–2 предложениях, зачем учить «{step.title}». Причина: {step.why}"
            result[step.skill] = self.ask(prompt)
        return result


def build_gateway() -> LlmGateway:
    from app.core.config import get_settings  # импорт здесь, чтобы шлюз можно было тестировать без настроек

    provider = get_settings().llm_provider
    if provider == "fake":
        return LlmGateway([FakeLlmClient()])
    return LlmGateway([GigaChatClient(), YandexGptClient()])
