"""Тесты построителя карты (TC-01, TC-02, TC-03 из плана тестирования)."""

import pytest

from app.modules.career_map.builder import MapBuilder, SkillGraph
from app.modules.career_map.demo_catalog import DemoCatalog
from app.modules.career_map.domain import RequiredSkill, SkillId, StepStatus

S = SkillId


def test_order_respects_prerequisites():
    """SQL идёт раньше фреймворка, фреймворк раньше командного проекта."""
    career_map = MapBuilder(DemoCatalog()).build("backend-junior", set())
    order = [s.skill.value for s in career_map.steps]

    assert order.index("python") < order.index("sql") < order.index("web-framework")
    assert order.index("web-framework") < order.index("team-project") < order.index("resume")


def test_same_input_gives_same_map():
    """Детерминированность (НФТ): два запуска — одна и та же карта."""
    skills = {S("python"), S("git")}
    first = MapBuilder(DemoCatalog()).build("backend-junior", skills)
    second = MapBuilder(DemoCatalog()).build("backend-junior", skills)

    assert [s.skill for s in first.steps] == [s.skill for s in second.steps]


def test_known_skills_are_done_and_one_step_is_current():
    career_map = MapBuilder(DemoCatalog()).build("backend-junior", {S("python"), S("git")})
    statuses = {s.skill.value: s.status for s in career_map.steps}

    assert statuses.get("python", StepStatus.DONE) == StepStatus.DONE
    assert sum(1 for s in career_map.steps if s.status == StepStatus.CURRENT) == 1
    assert career_map.current_step is not None
    assert career_map.current_step.skill == S("sql")


def test_map_has_6_to_8_steps():
    career_map = MapBuilder(DemoCatalog()).build("backend-junior", set())
    assert 6 <= len(career_map.steps) <= 8


class BrokenExplainer:
    def explain(self, career_map):
        raise TimeoutError("LLM не ответила")


def test_map_is_built_without_llm():
    """TC-03: LLM упала — карта всё равно есть, просто без пояснений."""
    career_map = MapBuilder(DemoCatalog(), BrokenExplainer()).build("backend-junior", set())

    assert len(career_map.steps) >= 6
    assert all(s.explanation is None for s in career_map.steps)


def test_cycle_in_catalog_is_reported():
    skills = [RequiredSkill(S("a"), "A"), RequiredSkill(S("b"), "B")]
    graph = SkillGraph({S("a"): {S("b")}, S("b"): {S("a")}})

    with pytest.raises(ValueError, match="цикл"):
        graph.order(skills)


def test_empty_skill_id_is_rejected():
    with pytest.raises(ValueError):
        SkillId("  ")
