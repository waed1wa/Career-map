"""Эталонный набор: разметка ссылается только на справочник, в резюме нет контактов.

Пока набор пустой, тесты помечаются как пропущенные. Как только в data/golden_set появятся
файлы, каждый проверяется на каждом пулл-реквесте.
"""

import json
import re
from pathlib import Path

import pytest

from app.modules.catalog.repository import load_catalog

GOLDEN = Path(__file__).resolve().parents[2] / "data" / "golden_set"
MARKUP = sorted(GOLDEN.glob("*.json"))
RESUMES = sorted(GOLDEN.glob("resume_*.txt"))

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?:\+7|\b8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}\b")


@pytest.mark.parametrize("path", MARKUP, ids=lambda p: p.name)
def test_markup_uses_catalog_ids(path: Path):
    catalog = load_catalog()
    data = json.loads(path.read_text(encoding="utf-8"))
    professions = {p.id for p in catalog.professions()}
    skills = {s.id for s in catalog.skills()}

    assert data["profession_id"] in professions
    unknown = (set(data["skills"]) | set(data.get("expected_steps", []))) - skills
    assert not unknown, f"Нет в справочнике: {sorted(unknown)}"


@pytest.mark.parametrize("path", RESUMES, ids=lambda p: p.name)
def test_resume_has_markup_and_no_contacts(path: Path):
    text = path.read_text(encoding="utf-8")

    assert path.with_suffix(".json").exists(), "У резюме нет файла разметки"
    assert not EMAIL.search(text), "В резюме осталась почта"
    assert not PHONE.search(text), "В резюме остался телефон"


def test_contact_patterns_work():
    """Проверяем саму проверку: иначе тест выше мог бы молча ничего не находить."""
    assert EMAIL.search("пишите на ivan.petrov@mail.ru")
    assert PHONE.search("тел. +7 (912) 345-67-89")
    assert PHONE.search("8 912 345 67 89")
    assert not PHONE.search("Python 3.12, опыт 2 года, 120 часов курса")
