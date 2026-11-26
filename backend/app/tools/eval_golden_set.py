"""Замер точности разбора резюме на золотом наборе (неделя 3, риск Р-6).

Запуск из папки backend:
    python -m app.tools.eval_golden_set          — только словарь
    python -m app.tools.eval_golden_set --llm    — LLM со словарём (нужны ключи в .env)

Точность — какая доля найденных навыков верная (нет ли лишних).
Полнота — какая доля навыков из разметки найдена (не пропустили ли).
Порог из плана: точность не ниже 80%. Ниже — скрипт завершается с ошибкой, это ранний сигнал Р-6.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from app.modules.catalog.repository import get_catalog
from app.modules.profile.resume_service import SkillSource
from app.modules.profile.skill_finder import SkillFinder

THRESHOLD = 0.8
DEFAULT_DIR = Path(__file__).resolve().parents[3] / "data" / "golden_set"


@dataclass(frozen=True)
class Case:
    name: str
    text: str
    expected: frozenset[str]


@dataclass(frozen=True)
class Score:
    hits: int  # нашли и это верно
    extra: int  # нашли, а в разметке нет
    missed: int  # в разметке есть, а не нашли

    @property
    def precision(self) -> float:
        found = self.hits + self.extra
        return self.hits / found if found else 1.0  # ничего не нашли — значит, и лишнего нет

    @property
    def recall(self) -> float:
        expected = self.hits + self.missed
        return self.hits / expected if expected else 1.0

    def __add__(self, other: "Score") -> "Score":
        return Score(self.hits + other.hits, self.extra + other.extra, self.missed + other.missed)


def score(expected: set[str] | frozenset[str], found: set[str]) -> Score:
    return Score(len(found & expected), len(found - expected), len(expected - found))


def load_cases(folder: Path) -> list[Case]:
    cases = []
    for text_file in sorted(folder.glob("resume_*.txt")):
        markup = json.loads(text_file.with_suffix(".json").read_text(encoding="utf-8"))
        cases.append(Case(text_file.stem, text_file.read_text(encoding="utf-8"), frozenset(markup["skills"])))
    return cases


def evaluate(cases: list[Case], source: SkillSource) -> list[tuple[Case, set[str], Score]]:
    rows = []
    for case in cases:
        found = {f.skill.value for f in source.find(case.text)}
        rows.append((case, found, score(case.expected, found)))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Точность разбора резюме на золотом наборе")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--llm", action="store_true", help="LLM со словарём вместо одного словаря")
    args = parser.parse_args(argv)

    cases = load_cases(args.dir)
    if not cases:
        print(f"В {args.dir} нет резюме. Как их добавить — в README.md этой папки.")
        return 2

    catalog = get_catalog()
    finder = SkillFinder(catalog)
    gateway = None
    source: SkillSource = finder
    if args.llm:
        from app.integrations.llm.gateway import build_gateway
        from app.modules.profile.llm_skills import SkillReader

        gateway = build_gateway()
        source = SkillReader(catalog, finder, gateway)

    rows = evaluate(cases, source)
    total = Score(0, 0, 0)
    print(f"{'резюме':<14} {'точность':>9} {'полнота':>8}  лишнее / пропущено")
    for case, found, s in rows:
        total = total + s
        extra = ", ".join(sorted(found - case.expected)) or "—"
        missed = ", ".join(sorted(case.expected - found)) or "—"
        print(f"{case.name:<14} {s.precision:>9.0%} {s.recall:>8.0%}  {extra} / {missed}")
    print(f"{'ИТОГО':<14} {total.precision:>9.0%} {total.recall:>8.0%}  ({len(rows)} резюме)")
    if gateway is not None:
        print(f"Токенов LLM на одно резюме в среднем: {gateway.tokens_used / len(rows):.0f}")

    if total.precision < THRESHOLD:
        print(f"Точность ниже {THRESHOLD:.0%} — сигнал риска Р-6, разбираем на ретро")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
