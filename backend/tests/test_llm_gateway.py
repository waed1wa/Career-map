"""LLM-шлюз: обезличивание (TC-04) и запасной провайдер."""

import pytest

from app.integrations.llm.gateway import FakeLlmClient, LlmGateway, LlmUnavailable, anonymize


def test_anonymize_removes_contacts():
    text = "Иван, ivan.petrov@mail.ru, +7 (912) 345-67-89, github: https://github.com/ivan, t.me/ivan"
    clean = anonymize(text)

    assert "ivan.petrov@mail.ru" not in clean
    assert "345-67-89" not in clean
    assert "github.com" not in clean
    assert "t.me" not in clean
    assert "[почта]" in clean and "[телефон]" in clean and "[ссылка]" in clean


def test_anonymize_keeps_skills():
    assert anonymize("Python, SQL, Docker") == "Python, SQL, Docker"


class Down:
    name = "down"

    def complete(self, prompt: str) -> str:
        raise TimeoutError


class Spy:
    name = "spy"

    def __init__(self) -> None:
        self.last_prompt = ""

    def complete(self, prompt: str) -> str:
        self.last_prompt = prompt
        return "ok"


def test_fallback_to_second_provider():
    gateway = LlmGateway([Down(), FakeLlmClient()])
    assert gateway.ask("вопрос")


def test_all_providers_down():
    with pytest.raises(LlmUnavailable):
        LlmGateway([Down(), Down()]).ask("вопрос")


def test_prompt_is_anonymized_before_sending():
    spy = Spy()
    LlmGateway([spy]).ask("моя почта a@b.ru")
    assert "a@b.ru" not in spy.last_prompt
