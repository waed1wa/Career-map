"""Разбор ответов провайдеров LLM на сохранённых примерах — без сети."""

import pytest

from app.integrations.llm.gateway import LlmUnavailable
from app.integrations.llm.responses import parse_gigachat, parse_yandexgpt, token_expires_at

GIGACHAT_OK = {
    "choices": [{"message": {"role": "assistant", "content": " Учите SQL. "}, "index": 0}],
    "usage": {"prompt_tokens": 40, "completion_tokens": 5, "total_tokens": 45},
}

YANDEX_OK = {
    "alternatives": [
        {"message": {"role": "assistant", "text": "Учите SQL."}, "status": "ALTERNATIVE_STATUS_FINAL"}
    ],
    "usage": {"inputTextTokens": "40", "completionTokens": "5", "totalTokens": "45"},
}


def test_gigachat_text_and_tokens():
    completion = parse_gigachat(GIGACHAT_OK)

    assert (completion.text, completion.tokens) == ("Учите SQL.", 45)


def test_gigachat_without_usage_counts_zero():
    assert parse_gigachat({"choices": [{"message": {"content": "Да"}}]}).tokens == 0


@pytest.mark.parametrize(
    "data",
    [{}, {"choices": []}, {"choices": [{"message": {"content": "   "}}]}, "не json-объект", None],
    ids=["empty", "no_choices", "blank_text", "string", "none"],
)
def test_gigachat_bad_answers(data):
    with pytest.raises(LlmUnavailable):
        parse_gigachat(data)


def test_yandex_text_and_tokens_from_strings():
    completion = parse_yandexgpt(YANDEX_OK)

    assert (completion.text, completion.tokens) == ("Учите SQL.", 45)


def test_yandex_answer_inside_result():
    """Старый формат ответа: всё внутри result."""
    assert parse_yandexgpt({"result": YANDEX_OK}).text == "Учите SQL."


def test_yandex_content_filter_is_unavailable():
    data = {"alternatives": [{"message": {"text": "…"}, "status": "ALTERNATIVE_STATUS_CONTENT_FILTER"}]}

    with pytest.raises(LlmUnavailable, match="фильтром"):
        parse_yandexgpt(data)


@pytest.mark.parametrize("data", [{}, {"alternatives": []}, {"result": None}, [1, 2]])
def test_yandex_bad_answers(data):
    with pytest.raises(LlmUnavailable):
        parse_yandexgpt(data)


@pytest.mark.parametrize(
    ("value", "seconds"),
    [(1_700_000_000, 1_700_000_000), (1_700_000_000_000, 1_700_000_000), ("1700000000", 1_700_000_000)],
    ids=["seconds", "milliseconds", "string"],
)
def test_token_expiry_units(value, seconds):
    assert token_expires_at(value) == seconds
