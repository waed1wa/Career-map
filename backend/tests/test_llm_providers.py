"""GigaChat и YandexGPT на поддельном HTTP (httpx.MockTransport). Тесты идут в CI, где есть httpx.

Проверяем то, что сломает подключение на стенде: заголовки, токен, повтор при 401, запасной провайдер.
"""

import uuid

import pytest

httpx = pytest.importorskip("httpx")

from app.integrations.llm.gateway import LlmGateway, LlmUnavailable  # noqa: E402
from app.integrations.llm.providers import GigaChatClient, YandexGptClient  # noqa: E402

OAUTH = "https://oauth.test/api/v2/oauth"
BASE = "https://giga.test/v1"
YANDEX = "https://yandex.test/foundationModels/v1/completion"


def chat_ok(text: str = "Ответ", tokens: int = 10) -> dict:
    return {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": tokens}}


class Recorder:
    """Подделка сервера: запоминает запросы и отвечает по сценарию."""

    def __init__(self, answers):
        self.requests: list[httpx.Request] = []
        self._answers = list(answers)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self._answers.pop(0)
        return httpx.Response(status, json=body)


def gigachat(server: Recorder, now: list[float]) -> GigaChatClient:
    return GigaChatClient(
        "a2V5",
        scope="GIGACHAT_API_PERS",
        model="GigaChat",
        base_url=BASE,
        oauth_url=OAUTH,
        http=httpx.Client(transport=httpx.MockTransport(server)),
        clock=lambda: now[0],
    )


TOKEN = (200, {"access_token": "t1", "expires_at": 1_000 + 1_800})
TOKEN_2 = (200, {"access_token": "t2", "expires_at": 9_999})


def test_gigachat_gets_token_then_asks():
    server = Recorder([TOKEN, (200, chat_ok("Учите SQL"))])

    assert gigachat(server, [1_000.0]).complete("вопрос") == "Учите SQL"

    oauth, chat = server.requests
    assert oauth.headers["Authorization"] == "Basic a2V5"
    uuid.UUID(oauth.headers["RqUID"])  # настоящий uuid, иначе сервер откажет
    assert oauth.content == b"scope=GIGACHAT_API_PERS"
    assert str(chat.url) == f"{BASE}/chat/completions"
    assert chat.headers["Authorization"] == "Bearer t1"


def test_gigachat_reuses_token_for_30_minutes():
    server = Recorder([TOKEN, (200, chat_ok()), (200, chat_ok())])
    now = [1_000.0]
    client = gigachat(server, now)

    client.complete("1")
    now[0] = 1_000 + 1_000  # прошло ~17 минут
    client.complete("2")

    assert [r.url.host for r in server.requests] == ["oauth.test", "giga.test", "giga.test"]


def test_gigachat_takes_new_token_when_old_expires():
    server = Recorder([TOKEN, (200, chat_ok()), TOKEN_2, (200, chat_ok())])
    now = [1_000.0]
    client = gigachat(server, now)

    client.complete("1")
    now[0] = 1_000 + 1_790  # до конца меньше минуты — берём новый заранее
    client.complete("2")

    assert server.requests[-1].headers["Authorization"] == "Bearer t2"


def test_gigachat_retries_once_after_401():
    server = Recorder([TOKEN, (401, {}), TOKEN_2, (200, chat_ok("Ок"))])

    assert gigachat(server, [1_000.0]).complete("вопрос") == "Ок"


def test_gigachat_counts_tokens():
    server = Recorder([TOKEN, (200, chat_ok(tokens=45)), (200, chat_ok(tokens=5))])
    client = gigachat(server, [1_000.0])

    client.complete("1")
    client.complete("2")

    assert client.tokens_used == 50


def test_gigachat_server_error_is_unavailable():
    server = Recorder([TOKEN, (500, {})])

    with pytest.raises(LlmUnavailable, match="500"):
        gigachat(server, [1_000.0]).complete("вопрос")


def yandex(server: Recorder) -> YandexGptClient:
    return YandexGptClient(
        "ya-key",
        folder_id="b1g",
        model="yandexgpt-lite/latest",
        url=YANDEX,
        http=httpx.Client(transport=httpx.MockTransport(server)),
    )


def test_yandex_request_format():
    server = Recorder([(200, {"alternatives": [{"message": {"text": "Ок"}}], "usage": {"totalTokens": "7"}})])
    client = yandex(server)

    assert client.complete("вопрос") == "Ок"

    request = server.requests[0]
    assert request.headers["Authorization"] == "Api-Key ya-key"
    assert request.headers["x-folder-id"] == "b1g"
    body = request.read().decode()
    assert '"modelUri":"gpt://b1g/yandexgpt-lite/latest"' in body.replace(" ", "")
    assert client.tokens_used == 7


def test_gateway_falls_back_to_yandex():
    """Р-4: GigaChat лежит — отвечает YandexGPT, пользователь ничего не замечает."""
    giga = gigachat(Recorder([TOKEN, (503, {})]), [1_000.0])
    ya = yandex(Recorder([(200, {"alternatives": [{"message": {"text": "Запасной ответ"}}]})]))

    assert LlmGateway([giga, ya]).ask("вопрос") == "Запасной ответ"


def test_gateway_without_providers_is_unavailable():
    with pytest.raises(LlmUnavailable):
        LlmGateway([]).ask("вопрос")


def test_build_gateway_order_and_missing_keys(monkeypatch):
    from app.core import config
    from app.integrations.llm import gateway

    monkeypatch.setenv("LLM_PROVIDER", "yandexgpt")
    monkeypatch.setenv("GIGACHAT_API_KEY", "a2V5")
    monkeypatch.setenv("YANDEXGPT_API_KEY", "ya-key")
    monkeypatch.setenv("YANDEXGPT_FOLDER_ID", "b1g")
    config.get_settings.cache_clear()
    try:
        names = [c.name for c in gateway.build_gateway()._clients]
        assert names == ["yandexgpt", "gigachat"]

        monkeypatch.setenv("YANDEXGPT_FOLDER_ID", "")  # без каталога YandexGPT не подключаем
        config.get_settings.cache_clear()
        assert [c.name for c in gateway.build_gateway()._clients] == ["gigachat"]
    finally:
        config.get_settings.cache_clear()
