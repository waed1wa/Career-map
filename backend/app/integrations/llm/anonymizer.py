"""Обезличивание текста перед отправкой в LLM (правило системы: ПДн не уходят в LLM, 152-ФЗ)."""

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
_URL = re.compile(r"(?:https?://|www\.|t\.me/|vk\.com/)\S+", re.IGNORECASE)


def anonymize(text: str) -> str:
    """Убирает почту, телефоны и ссылки на профили (тест TC-04)."""
    text = _EMAIL.sub("[почта]", text)
    text = _URL.sub("[ссылка]", text)
    return _PHONE.sub("[телефон]", text)
