"""Навыки из резюме через LLM. Сама LLM здесь поддельная: проверяем, что мы делаем с её ответом.

Классы ответов LLM (лекция 9): чистый JSON, JSON в тексте или в блоке кода, выдуманный навык,
не JSON, не список, пустой список, LLM недоступна.
"""

import pytest

from app.integrations.llm.gateway import LlmUnavailable
from app.modules.catalog.repository import load_catalog
from app.modules.profile.llm_skills import (
    MAX_RESUME_CHARS,
    LlmAnswerError,
    SkillReader,
    build_prompt,
    parse_skill_ids,
)
from app.modules.profile.skill_finder import SkillFinder

catalog = load_catalog()
KNOWN = {s.id for s in catalog.skills()}


class FakeLlm:
    def __init__(self, answer: str | Exception):
        self.answer = answer
        self.prompts: list[str] = []

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def reader(answer: str | Exception | None) -> SkillReader:
    llm = None if answer is None else FakeLlm(answer)
    return SkillReader(catalog, SkillFinder(catalog), llm)


# ---------- разбор ответа LLM ----------


@pytest.mark.parametrize(
    "answer",
    [
        '["python", "sql"]',
        'Вот навыки: ["python", "sql"]. Удачи!',
        '```json\n["python", "sql"]\n```',
        '["Python", " sql "]',
        '{"skills": ["python", "sql"]}',
    ],
    ids=["clean_json", "json_in_text", "code_block", "case_and_spaces", "array_inside_object"],
)
def test_answers_that_we_understand(answer):
    assert parse_skill_ids(answer, KNOWN) == (["python", "sql"], [])


def test_made_up_skills_are_dropped():
    """Р-3: LLM придумала навык, которого нет в справочнике, — на карту он не попадёт."""
    assert parse_skill_ids('["python", "kotlin", "blockchain"]', KNOWN) == (
        ["python"],
        ["kotlin", "blockchain"],
    )


def test_empty_list_is_a_valid_answer():
    assert parse_skill_ids("[]", KNOWN) == ([], [])


def test_duplicates_are_removed():
    assert parse_skill_ids('["git", "git"]', KNOWN) == (["git"], [])


@pytest.mark.parametrize(
    "answer",
    ["Навыки: Python и SQL", "[1, 2]", '["python"', ""],
    ids=["no_json", "not_strings", "broken_json", "empty"],
)
def test_answers_we_reject(answer):
    with pytest.raises(LlmAnswerError):
        parse_skill_ids(answer, KNOWN)


# ---------- запрос ----------


def test_prompt_lists_catalog_and_contains_resume():
    prompt = build_prompt("Делал сайт на React", catalog)

    assert "- react: React" in prompt
    assert "Делал сайт на React" in prompt
    assert "JSON" in prompt


def test_long_resume_is_cut():
    prompt = build_prompt("а" * (MAX_RESUME_CHARS + 500), catalog)

    assert "а" * MAX_RESUME_CHARS in prompt
    assert "а" * (MAX_RESUME_CHARS + 1) not in prompt


# ---------- выбор способа ----------


def test_llm_adds_skills_said_in_own_words():
    """Словарь нашёл Python, LLM поняла из описания, что был командный проект."""
    result = reader('["python", "team-project"]').read("Python. Вчетвером сделали бота для деканата.")

    assert [s.skill.value for s in result.skills] == ["python", "team-project"]
    assert result.method == "llm+dictionary"
    by_id = {s.skill.value: s for s in result.skills}
    assert by_id["python"].matched == "Python"  # словарь знает, где это написано
    assert by_id["team-project"].source == "llm"


def test_dictionary_finds_what_llm_missed():
    result = reader('["python"]').read("Python, Docker")

    assert [s.skill.value for s in result.skills] == ["python", "docker"]


def test_llm_unavailable_falls_back_to_dictionary():
    """TC-03 / Р-4: LLM лежит — навыки всё равно есть."""
    result = reader(LlmUnavailable("таймаут")).read("Python, Docker")

    assert [s.skill.value for s in result.skills] == ["python", "docker"]
    assert result.method == "dictionary"


def test_strange_llm_answer_falls_back_to_dictionary():
    result = reader("Я не могу ответить на этот вопрос").read("Python")

    assert result.method == "dictionary"
    assert [s.skill.value for s in result.skills] == ["python"]


def test_without_llm_only_dictionary():
    assert reader(None).read("SQL").method == "dictionary"


def test_dropped_skills_are_reported():
    assert reader('["python", "kotlin"]').read("Python").dropped == ["kotlin"]
