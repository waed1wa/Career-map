"""Разбор ответов GigaChat и YandexGPT. Без сети — чтобы проверять тестами на сохранённых ответах.

Любой ответ не того вида превращаем в LlmUnavailable: для шлюза это то же самое, что провайдер
молчит, и он переходит к запасному (риск Р-4).
"""

from dataclasses import dataclass
from typing import Any

from app.integrations.llm.gateway import LlmUnavailable


@dataclass(frozen=True)
class Completion:
    text: str
    tokens: int  # сколько токенов ушло на запрос и ответ — считаем расходы (риск Р-5)


def parse_gigachat(data: Any) -> Completion:
    """Ответ GigaChat в формате OpenAI: choices[0].message.content, usage.total_tokens."""
    try:
        text = data["choices"][0]["message"]["content"]
        tokens = int(data.get("usage", {}).get("total_tokens", 0))
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise LlmUnavailable(f"Непонятный ответ GigaChat: {error!r}") from error
    return _checked(text, tokens, "GigaChat")


def parse_yandexgpt(data: Any) -> Completion:
    """Ответ YandexGPT: alternatives[0].message.text, usage.totalTokens (строка).

    В разных версиях документации alternatives лежит то в корне, то внутри result — понимаем оба.
    """
    try:
        root = data.get("result", data)
        alternative = root["alternatives"][0]
        if alternative.get("status") == "ALTERNATIVE_STATUS_CONTENT_FILTER":
            raise LlmUnavailable("YandexGPT скрыл ответ фильтром")
        text = alternative["message"]["text"]
        tokens = int(root.get("usage", {}).get("totalTokens", 0))
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
        raise LlmUnavailable(f"Непонятный ответ YandexGPT: {error!r}") from error
    return _checked(text, tokens, "YandexGPT")


def token_expires_at(value: Any) -> float:
    """Когда истекает токен GigaChat, в секундах. Сервер может прислать время в миллисекундах."""
    moment = float(value)
    return moment / 1000 if moment > 1e12 else moment


def _checked(text: Any, tokens: int, provider: str) -> Completion:
    if not isinstance(text, str) or not text.strip():
        raise LlmUnavailable(f"{provider} вернул пустой ответ")
    return Completion(text=text.strip(), tokens=tokens)
