"""Шесть вопросов опроса — второй способ войти без резюме (ФП-3 из CJM).

Вопросы короткие и про то, что студент уже делал руками, а не «оцените себя от 1 до 10»:
на вопрос про конкретное дело проще ответить честно, чем оценить себя.
Каждый навык справочника можно отметить хотя бы одним вариантом — это проверяет тест.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Kind(StrEnum):
    SINGLE = "single"  # ровно один вариант
    MULTI = "multi"  # один или несколько


@dataclass(frozen=True)
class Option:
    id: str
    text: str
    skills: tuple[str, ...] = ()  # какие навыки справочника засчитываем
    profession: str | None = None  # какую профессию выбирает этот вариант
    exclusive: bool = False  # «Ничего из этого» — нельзя выбрать вместе с другими


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    kind: Kind
    options: tuple[Option, ...] = field(default_factory=tuple)


QUESTIONS: tuple[Question, ...] = (
    Question(
        "goal",
        "Кем вы хотите работать?",
        Kind.SINGLE,
        (
            Option("backend", "Бэкенд-разработчиком", profession="backend-junior"),
            Option("frontend", "Фронтенд-разработчиком", profession="frontend-junior"),
            Option("analyst", "Аналитиком данных", profession="data-analyst-junior"),
            Option("not-sure", "Пока не знаю"),
        ),
    ),
    Question(
        "interest",
        "Что вам интереснее?",
        Kind.SINGLE,
        (
            Option("server", "Как всё устроено внутри: данные, логика, сервер", profession="backend-junior"),
            Option("interface", "То, что видит и нажимает пользователь", profession="frontend-junior"),
            Option("numbers", "Искать закономерности в цифрах", profession="data-analyst-junior"),
        ),
    ),
    Question(
        "languages",
        "На чём вы уже писали код сами, не только на паре?",
        Kind.MULTI,
        (
            Option("python", "Python", skills=("python",)),
            Option("javascript", "JavaScript", skills=("javascript",)),
            Option("typescript", "TypeScript", skills=("typescript", "javascript")),
            Option("sql", "SQL-запросы", skills=("sql",)),
            Option("none", "Пока ни на чём", exclusive=True),
        ),
    ),
    Question(
        "practice",
        "Что из этого вы уже делали?",
        Kind.MULTI,
        (
            Option("git", "Делал коммиты и ветки в Git", skills=("git",)),
            Option("linux", "Работал в командной строке Linux", skills=("linux",)),
            Option("html", "Верстал страницу на HTML и CSS", skills=("html-css",)),
            Option("react", "Делал интерфейс на React", skills=("react",)),
            Option("api", "Делал API на FastAPI, Django или Flask", skills=("web-framework",)),
            Option("tests", "Писал автотесты", skills=("testing",)),
            Option("docker", "Запускал проект в Docker", skills=("docker",)),
            Option("charts", "Строил графики или дашборды", skills=("data-viz",)),
            Option("none", "Ничего из этого", exclusive=True),
        ),
    ),
    Question(
        "topics",
        "Какие темы вы уже понимаете и могли бы объяснить однокурснику?",
        Kind.MULTI,
        (
            Option("oop", "Классы и объекты (ООП)", skills=("oop",)),
            Option("http", "Как устроены HTTP-запросы и API", skills=("http-api",)),
            Option("statistics", "Статистика и теория вероятностей", skills=("statistics",)),
            Option("excel", "Формулы и сводные таблицы в Excel", skills=("excel",)),
            Option("pandas", "Анализ данных в pandas", skills=("pandas",)),
            Option("figma", "Макеты в Figma", skills=("figma",)),
            Option("none", "Ничего из этого", exclusive=True),
        ),
    ),
    Question(
        "experience",
        "Что у вас уже есть?",
        Kind.MULTI,
        (
            Option("team", "Проект в команде, который довели до конца", skills=("team-project",)),
            Option("resume", "Резюме, с которым откликался на стажировки", skills=("resume",)),
            Option("none", "Пока ничего", exclusive=True),
        ),
    ),
)
