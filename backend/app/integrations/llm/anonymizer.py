"""Обезличивание текста перед отправкой в LLM (правило системы: ПДн не уходят в LLM, 152-ФЗ).

Что убираем: почту, телефоны, ссылки на профили и ФИО.
ФИО ищем правилами, а не нейросетью: правила работают без внешних моделей, быстро и
предсказуемо, их легко покрыть тестами. Если на золотом наборе правила начнут пропускать
имена, следующим шагом подключим библиотеку Natasha (распознавание имён в русском тексте).
"""

import re

NAME = "[имя]"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
_URL = re.compile(r"(?:https?://|www\.|t\.me/|vk\.com/)\S+", re.IGNORECASE)

# Слово с заглавной буквы, в том числе двойная фамилия через дефис: «Римский-Корсаков».
_WORD = r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?"
# Отчество узнаём по окончанию: Петрович, Ильич, Петровна, Никитична.
_PATRONYMIC = r"[А-ЯЁ][а-яё]+(?:вич|ьич|вна|ична)"
_INITIALS = r"[А-ЯЁ]\.\s?[А-ЯЁ]\."

# Поля резюме вида «ФИО: ...» — убираем значение до конца строки.
_LABELED = re.compile(r"(?im)^(\s*(?:фио|имя|фамилия|отчество)\s*[:\-–]\s*).+$")
# Порядок важен: сначала длинные варианты (три слова), потом короткие.
_FULL_NAME = re.compile(
    rf"\b{_WORD}\s+{_WORD}\s+{_PATRONYMIC}\b"  # Иванов Иван Петрович
    rf"|\b{_WORD}\s+{_PATRONYMIC}\s+{_WORD}\b"  # Иван Петрович Иванов
    rf"|\b{_WORD}\s+{_PATRONYMIC}\b"  # Анна Сергеевна
    rf"|\b{_WORD}\s+{_INITIALS}"  # Иванов И. П.
    rf"|{_INITIALS}\s?{_WORD}\b"  # И.П. Иванов
)
# Первая строка резюме из 2–3 слов с заглавной буквы — почти всегда имя.
_FIRST_LINE_NAME = re.compile(rf"^\s*{_WORD}(?:\s+{_WORD}){{1,2}}\s*$")
# ...но не заголовок вроде «Резюме студента».
_NOT_A_NAME = {"резюме", "студент", "студента", "разработчик", "аналитик", "тестировщик", "стажёр", "стажер"}


def _remove_name_in_first_line(text: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        words = {w.lower() for w in line.split()}
        if _FIRST_LINE_NAME.match(line) and not words & _NOT_A_NAME:
            lines[i] = NAME
        break  # смотрим только на первую непустую строку
    return "\n".join(lines)


def anonymize(text: str) -> str:
    """Убирает почту, телефоны, ссылки и ФИО (тест TC-04, находка Н-1)."""
    text = _EMAIL.sub("[почта]", text)
    text = _URL.sub("[ссылка]", text)
    text = _PHONE.sub("[телефон]", text)
    text = _LABELED.sub(rf"\g<1>{NAME}", text)
    text = _FULL_NAME.sub(NAME, text)
    return _remove_name_in_first_line(text)
