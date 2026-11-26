"""LLM-шлюз — адаптер для порта Explainer.

Правила из архитектуры:
- в LLM уходит только обезличенный текст (ПДн не покидают наш сервер, 152-ФЗ);
- LLM пишет пояснения, но не выбирает шаги и материалы;
- если основной провайдер не ответил — пробуем запасной, если и он молчит — карта без пояснений.
"""

import logging
from typing import Protocol

from app.integrations.llm.anonymizer import anonymize
from app.modules.career_map.domain import CareerMap, SkillId

log = logging.getLogger(__name__)

__all__ = ["LlmGateway", "LlmUnavailable", "anonymize", "build_gateway"]


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


class LlmGateway:
    """Перебирает провайдеров по очереди. Реализует порт Explainer."""

    def __init__(self, clients: list[LlmClient]):
        self._clients = clients

    @property
    def tokens_used(self) -> int:
        """Сколько токенов потратили все провайдеры — для подсчёта расходов (риск Р-5)."""
        return sum(getattr(c, "tokens_used", 0) for c in self._clients)

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

    settings = get_settings()
    if settings.llm_provider == "fake":
        return LlmGateway([FakeLlmClient()])

    from app.integrations.llm.providers import GigaChatClient, YandexGptClient  # httpx нужен только здесь

    clients: list[LlmClient] = []
    if settings.gigachat_api_key:
        clients.append(GigaChatClient.from_settings(settings))
    if settings.yandexgpt_api_key and settings.yandexgpt_folder_id:
        clients.append(YandexGptClient.from_settings(settings))
    if settings.llm_provider == "yandexgpt":
        clients.reverse()  # основной — тот, что указан в LLM_PROVIDER
    if not clients:
        log.warning("Ключей LLM нет: карта будет без пояснений, навыки — по словарю")
    return LlmGateway(clients)
