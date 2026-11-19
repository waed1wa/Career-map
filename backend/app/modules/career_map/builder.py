"""Построитель карты. Логика детерминированная: одинаковый вход — одинаковая карта.

Шаги 1–6 не используют LLM и случайность. LLM подключается только в конце, через порт Explainer,
и если она не ответила, карта всё равно строится — просто без пояснений.
"""

import logging

from app.modules.career_map.domain import CareerMap, MapStep, RequiredSkill, SkillId, StepStatus
from app.modules.career_map.ports import CatalogRepository, Explainer

log = logging.getLogger(__name__)

MIN_STEPS = 6
MAX_STEPS = 8


class SkillGraph:
    """Граф порядка изучения навыков (skill_prerequisites)."""

    def __init__(self, prerequisites: dict[SkillId, set[SkillId]]):
        self._pre = prerequisites

    def order(self, skills: list[RequiredSkill]) -> list[RequiredSkill]:
        """Топологическая сортировка. При равенстве — по id навыка, чтобы порядок был стабильным."""
        by_id = {s.skill: s for s in skills}
        result: list[RequiredSkill] = []
        visited: set[SkillId] = set()
        in_progress: set[SkillId] = set()

        def visit(skill_id: SkillId) -> None:
            if skill_id in visited or skill_id not in by_id:
                return
            if skill_id in in_progress:
                raise ValueError(f"В справочнике цикл в порядке изучения: {skill_id.value}")
            in_progress.add(skill_id)
            for pre in sorted(self._pre.get(skill_id, set())):
                visit(pre)
            in_progress.discard(skill_id)
            visited.add(skill_id)
            result.append(by_id[skill_id])

        for skill_id in sorted(by_id):
            visit(skill_id)
        return result


class GapCalculator:
    """Чего не хватает студенту до профессии."""

    @staticmethod
    def missing(required: list[RequiredSkill], user_skills: set[SkillId]) -> list[RequiredSkill]:
        return [s for s in required if s.skill not in user_skills]


class StepSelector:
    """Выбирает 6–8 шагов: сначала все недостающие, потом уже закрытые, чтобы карта не была пустой."""

    @staticmethod
    def select(ordered: list[RequiredSkill], user_skills: set[SkillId]) -> list[RequiredSkill]:
        missing = GapCalculator.missing(ordered, user_skills)
        done = [s for s in ordered if s.skill in user_skills]
        chosen = missing[:MAX_STEPS]
        if len(chosen) < MIN_STEPS:
            chosen += done[-(MIN_STEPS - len(chosen)) :] if done else []
        keep = {s.skill for s in chosen}
        return [s for s in ordered if s.skill in keep]  # сохраняем порядок изучения


class MapBuilder:
    def __init__(self, catalog: CatalogRepository, explainer: Explainer | None = None):
        self._catalog = catalog
        self._explainer = explainer

    def build(self, profession_id: str, user_skills: set[SkillId]) -> CareerMap:
        required = self._catalog.required_skills(profession_id)
        ordered = SkillGraph(self._catalog.prerequisites()).order(required)
        selected = StepSelector.select(ordered, user_skills)
        # пройденные шаги показываем в начале карты, порядок внутри групп не меняется
        selected.sort(key=lambda s: s.skill not in user_skills)

        steps: list[MapStep] = []
        current_set = False
        for i, s in enumerate(selected, start=1):
            if s.skill in user_skills:
                status = StepStatus.DONE
            elif not current_set:
                status, current_set = StepStatus.CURRENT, True
            else:
                status = StepStatus.TODO
            steps.append(MapStep(order=i, skill=s.skill, title=s.title, status=status, why=s.why))

        career_map = CareerMap(profession_id=profession_id, steps=steps)
        self._add_explanations(career_map)
        return career_map

    def _add_explanations(self, career_map: CareerMap) -> None:
        if self._explainer is None:
            return
        try:
            texts = self._explainer.explain(career_map)
        except Exception:  # LLM недоступна — инвариант «карта строится и без LLM»
            log.warning("Пояснения не получены, карта остаётся без них")
            return
        for step in career_map.steps:
            step.explanation = texts.get(step.skill)
