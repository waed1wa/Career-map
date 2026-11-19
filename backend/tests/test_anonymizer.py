"""Обезличивание перед LLM: находка Н-1 из валидации архитектуры (ФИО уходило в LLM).

Тесты построены по классам эквивалентности (лекция 9): каждый класс — свой способ записать имя.
"""

import pytest

from app.integrations.llm.anonymizer import anonymize


@pytest.mark.parametrize(
    "text",
    [
        "Иванов Иван Петрович",  # фамилия, имя, отчество
        "Иван Петрович Иванов",  # имя, отчество, фамилия
        "Анна Сергеевна",  # имя и отчество без фамилии
        "Римский-Корсаков Николай Андреевич",  # двойная фамилия
        "Иванов И. П.",  # фамилия с инициалами
        "И.П. Иванов",  # инициалы перед фамилией
    ],
    ids=[
        "surname-name-patronymic",
        "name-patronymic-surname",
        "name-patronymic",
        "double-surname",
        "surname-initials",
        "initials-surname",
    ],
)
def test_name_forms_are_removed(text):
    clean = anonymize(f"Руководитель практики: {text}, отзыв положительный")

    assert text not in clean
    assert "[имя]" in clean


def test_labeled_fields_are_removed():
    clean = anonymize("ФИО: Смирнова Ольга\nИмя: Оля\nНавыки: Python")

    assert "Смирнова" not in clean and "Оля" not in clean
    assert "ФИО: [имя]" in clean
    assert "Навыки: Python" in clean


def test_name_in_first_line_is_removed():
    """В резюме имя обычно стоит первой строкой и часто без отчества."""
    clean = anonymize("Петров Сергей\nPython-разработчик\nНавыки: SQL, Docker")

    assert "Петров" not in clean
    assert clean.startswith("[имя]")


def test_first_line_title_is_kept():
    """Заголовок «Резюме студента» — не имя, его не трогаем (класс «похоже, но не имя»)."""
    clean = anonymize("Резюме студента\nНавыки: Python")

    assert clean.startswith("Резюме студента")


def test_full_resume_example():
    """Сценарий из валидации: строка, на которой нашли проблему."""
    text = "Иванов Иван Петрович, ivan@mail.ru, +7 912 345-67-89, https://github.com/ivan, Python, SQL"

    clean = anonymize(text)

    assert "Иванов" not in clean and "Иван " not in clean and "Петрович" not in clean
    assert clean == "[имя], [почта], [телефон], [ссылка] Python, SQL"


@pytest.mark.parametrize(
    "text",
    [
        "Python, SQL, Docker",
        "Основы Python и Git",
        "Учился в Москве, проект для Студенческого совета",
        "Работал с FastAPI и PostgreSQL",
    ],
    ids=["skills", "skills-in-phrase", "city-and-org", "tech-names"],
)
def test_skills_and_ordinary_words_are_kept(text):
    """Навыки нельзя терять: без них не построить карту."""
    assert anonymize(text) == text
