"""Временный справочник в памяти для демо-карты и тестов.

В спринте 3 его заменит SqlCatalogRepository с 60 навыками из базы (адаптер того же порта).
"""

from app.modules.career_map.domain import RequiredSkill, SkillId

_S = SkillId

_BACKEND = [
    RequiredSkill(_S("python"), "Основы Python", "Язык большинства вакансий для джунов в бэкенде"),
    RequiredSkill(_S("git"), "Git и GitHub", "Без него не возьмут в командный проект"),
    RequiredSkill(_S("sql"), "SQL и базы данных", "SQL есть почти в каждой вакансии"),
    RequiredSkill(_S("web-framework"), "FastAPI или Django", "Чтобы сделать своё первое API"),
    RequiredSkill(_S("team-project"), "Первый проект в команде", "Строка опыта в резюме"),
    RequiredSkill(_S("docker"), "Docker и деплой", "Показать проект работающим"),
    RequiredSkill(_S("resume"), "Резюме и отклики", "Собрать всё и подаваться на стажировки"),
]

_PREREQ: dict[SkillId, set[SkillId]] = {
    _S("web-framework"): {_S("python"), _S("sql")},
    _S("sql"): {_S("python")},
    _S("team-project"): {_S("git"), _S("web-framework")},
    _S("docker"): {_S("web-framework")},
    _S("resume"): {_S("team-project")},
}


class DemoCatalog:
    def required_skills(self, profession_id: str) -> list[RequiredSkill]:
        if profession_id != "backend-junior":
            raise KeyError(f"Нет профессии {profession_id} в демо-справочнике")
        return list(_BACKEND)

    def prerequisites(self) -> dict[SkillId, set[SkillId]]:
        return dict(_PREREQ)
