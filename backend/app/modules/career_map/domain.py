"""Доменная модель карты — ядро гексагональной схемы (уровень 4 C4).

Ни от чего не зависит: ни от базы, ни от LLM.
"""

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True, order=True)
class SkillId:
    """Объект-значение: два SkillId с одинаковым значением — один и тот же навык."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("SkillId не может быть пустым")


@dataclass(frozen=True)
class RequiredSkill:
    skill: SkillId
    title: str
    why: str = ""  # «Зачем этот шаг» из справочника; LLM может переписать пояснение, но не шаг


class StepStatus(StrEnum):
    DONE = "done"
    CURRENT = "current"
    TODO = "todo"


@dataclass
class MapStep:
    order: int
    skill: SkillId
    title: str
    status: StepStatus
    why: str = ""
    explanation: str | None = None  # текст от LLM, может отсутствовать


@dataclass
class CareerMap:
    profession_id: str
    steps: list[MapStep] = field(default_factory=list)

    @property
    def steps_left(self) -> int:
        return sum(1 for s in self.steps if s.status != StepStatus.DONE)

    @property
    def current_step(self) -> MapStep | None:
        return next((s for s in self.steps if s.status == StepStatus.CURRENT), None)
