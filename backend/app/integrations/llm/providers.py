"""Настоящие провайдеры LLM: GigaChat (основной) и YandexGPT (запасной).

Оба — адаптеры порта LlmClient. Шлюз перебирает их по очереди с таймаутом 10 секунд (риск Р-4).
В запрос уходит только обезличенный текст: его готовит шлюз до вызова complete().
"""

import time
import uuid
from collections.abc import Callable

import httpx

from app.core.config import Settings
from app.integrations.llm.gateway import LlmUnavailable
from app.integrations.llm.responses import parse_gigachat, parse_yandexgpt, token_expires_at

TEMPERATURE = 0.2  # ниже — ответы стабильнее, нам нужна не фантазия, а аккуратность (риск Р-3)
TOKEN_MARGIN_SECONDS = 60  # обновляем токен заранее, а не в последнюю секунду


class GigaChatClient:
    name = "gigachat"

    def __init__(
        self,
        auth_key: str,
        *,
        scope: str,
        model: str,
        base_url: str,
        oauth_url: str,
        http: httpx.Client,
        clock: Callable[[], float] = time.time,
    ):
        self._auth_key = auth_key
        self._scope = scope
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._oauth_url = oauth_url
        self._http = http
        self._clock = clock
        self._token: str | None = None
        self._token_until = 0.0
        self.tokens_used = 0

    @classmethod
    def from_settings(cls, settings: Settings) -> "GigaChatClient":
        verify: str | bool = settings.gigachat_ca_bundle or True
        http = httpx.Client(timeout=settings.llm_timeout_seconds, verify=verify)
        return cls(
            settings.gigachat_api_key,
            scope=settings.gigachat_scope,
            model=settings.gigachat_model,
            base_url=settings.gigachat_base_url,
            oauth_url=settings.gigachat_oauth_url,
            http=http,
        )

    def complete(self, prompt: str) -> str:
        response = self._chat(prompt)
        if response.status_code == 401:  # токен отозвали раньше срока — берём новый один раз
            self._token = None
            response = self._chat(prompt)
        _raise_for_status(response, "GigaChat")
        completion = parse_gigachat(response.json())
        self.tokens_used += completion.tokens
        return completion.text

    def _chat(self, prompt: str) -> httpx.Response:
        return self._http.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._access_token()}", "Accept": "application/json"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
            },
        )

    def _access_token(self) -> str:
        """Токен живёт 30 минут — храним и берём новый только когда старый почти истёк."""
        if self._token and self._clock() < self._token_until - TOKEN_MARGIN_SECONDS:
            return self._token
        response = self._http.post(
            self._oauth_url,
            headers={
                "Authorization": f"Basic {self._auth_key}",
                "RqUID": str(uuid.uuid4()),
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"scope": self._scope},
        )
        _raise_for_status(response, "GigaChat (токен)")
        try:
            data = response.json()
            self._token = str(data["access_token"])
            self._token_until = token_expires_at(data["expires_at"])
        except (KeyError, ValueError, TypeError) as error:
            raise LlmUnavailable("GigaChat не выдал токен") from error
        return self._token


class YandexGptClient:
    name = "yandexgpt"

    def __init__(self, api_key: str, *, folder_id: str, model: str, url: str, http: httpx.Client):
        self._api_key = api_key
        self._folder_id = folder_id
        self._model_uri = f"gpt://{folder_id}/{model}"
        self._url = url
        self._http = http
        self.tokens_used = 0

    @classmethod
    def from_settings(cls, settings: Settings) -> "YandexGptClient":
        return cls(
            settings.yandexgpt_api_key,
            folder_id=settings.yandexgpt_folder_id,
            model=settings.yandexgpt_model,
            url=settings.yandexgpt_url,
            http=httpx.Client(timeout=settings.llm_timeout_seconds),
        )

    def complete(self, prompt: str) -> str:
        response = self._http.post(
            self._url,
            headers={"Authorization": f"Api-Key {self._api_key}", "x-folder-id": self._folder_id},
            json={
                "modelUri": self._model_uri,
                "completionOptions": {"stream": False, "temperature": TEMPERATURE, "maxTokens": "1000"},
                "messages": [{"role": "user", "text": prompt}],
            },
        )
        _raise_for_status(response, "YandexGPT")
        completion = parse_yandexgpt(response.json())
        self.tokens_used += completion.tokens
        return completion.text


def _raise_for_status(response: httpx.Response, provider: str) -> None:
    if response.status_code != 200:
        raise LlmUnavailable(f"{provider} ответил {response.status_code}")
