"""Part 7 ch.2: Quality gate evaluation engine."""

from __future__ import annotations

import operator
from dataclasses import dataclass

from qros.pipeline.stages import CriterionSpec, StageDef

_OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


@dataclass(frozen=True)
class CriterionEvaluation:
    criterion: CriterionSpec
    actual: float | bool
    passed: bool


def evaluate_criterion(crit: CriterionSpec, ctx: dict) -> CriterionEvaluation:
    actual = ctx.get(crit.field)
    if actual is None:
        return CriterionEvaluation(criterion=crit, actual=None, passed=False)
    op = _OPERATORS[crit.operator]
    try:
        passed = bool(op(actual, crit.target))
    except TypeError:
        passed = False
    return CriterionEvaluation(criterion=crit, actual=actual, passed=passed)


def evaluate_exit_criteria(stage: StageDef, ctx: dict) -> list[CriterionEvaluation]:
    return [evaluate_criterion(c, ctx) for c in stage.exit_criteria]


def all_pass(evals: list[CriterionEvaluation]) -> bool:
    return all(e.passed for e in evals)


def missing_artifacts(stage: StageDef, produced: set[str]) -> list[str]:
    return [o for o in stage.outputs if o not in produced]