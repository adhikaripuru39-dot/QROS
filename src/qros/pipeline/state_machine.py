"""Part 7: Research Pipeline state machine — linear, gatekeeper-controlled.

Transitioning between stages requires: all exit criteria of the current stage
satisfied AND all required artifacts produced. On gate failure the run halts and
(per the failure protocol) the hypothesis is marked REJECTED or returned to
Stage 3 for re-formulation. Retroactive threshold relaxation is prohibited.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from qros.hypothesis.registry import HypothesisDoc
from qros.pipeline.gates import all_pass, evaluate_exit_criteria, missing_artifacts
from qros.pipeline.stages import StageDef, get_stage


class PipelineHalted(Exception):
    """Raised when a stage gate evaluation blocks advancement."""


@dataclass
class ProjectRun:
    project_id: str
    hypothesis_id: str
    current_stage: int
    status: str  # ACTIVE | REJECTED | COMPLETED
    artifacts: dict[str, set[str]] = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    stage_history: list[dict] = field(default_factory=list)


class ResearchPipeline:
    """Drive a hypothesis through the 15-stage gatekeeper workflow."""

    def __init__(self, hypothesis: HypothesisDoc, project_id: str = ""):
        self.hypothesis = hypothesis
        self.project_id = project_id or hypothesis.hypothesis_id
        self.run = ProjectRun(
            project_id=self.project_id,
            hypothesis_id=hypothesis.hypothesis_id,
            current_stage=1,
            status="ACTIVE",
        )

    def stage(self) -> int:
        return self.run.current_stage

    def stage_def(self) -> StageDef:
        return get_stage(self.run.current_stage)

    def present_artifact(self, stage: int, artifact: str) -> None:
        """Declare that an artifact has been produced for a stage."""
        outputs = get_stage(stage).outputs
        if artifact not in outputs:
            raise ValueError(f"{artifact!r} is not a declared output of stage {stage}: {outputs}")
        self.run.artifacts.setdefault(stage, set()).add(artifact)

    @property
    def _produced_for_current(self) -> set[str]:
        return self.run.artifacts.get(self.run.current_stage, set())

    def set_context(self, **kv) -> None:
        """Feed measured gate values (e.g., max_adf_p, oos_sharpe) into context."""
        self.run.context.update(kv)

    def evaluate_current(self) -> dict:
        """Return {artifacts_missing, criteria, criteria_pass} for the current stage."""
        stage = self.stage_def()
        missing = missing_artifacts(stage, self._produced_for_current)
        evals = evaluate_exit_criteria(stage, self.run.context)
        pass_ = all_pass(evals)
        return {"stage": stage.number, "missing": missing, "criteria": [e.criterion.id for e in evals], "passing": pass_}

    def can_advance_to(self, stage: int) -> bool:
        """True when the pipeline may advance from its current stage."""
        cur = self.stage_def()
        missing = missing_artifacts(cur, self._produced_for_current)
        if missing:
            return False
        evals = evaluate_exit_criteria(cur, self.run.context)
        return all_pass(evals) and self.run.current_stage + 1 == stage

    def advance(self, allow_return_to_stage3: bool = False) -> ProjectRun:
        """Advance to the next stage, or halt with PipelineHalted on gate failure.

        Follows the Part 7 ch.2 failure protocol: the reason is recorded and the
        hypothesis marked REJECTED (or returned to Stage 3 when allowed).
        """
        cur = self.stage_def()
        missing = missing_artifacts(cur, self._produced_for_current)
        evals = evaluate_exit_criteria(cur, self.run.context)
        if missing or not all_pass(evals):
            failure = {
                "stage": cur.number,
                "name": cur.name,
                "missing_artifacts": missing,
                "criteria": [
                    {"id": e.criterion.id, "actual": e.actual, "passed": e.passed} for e in evals
                ],
            }
            self.run.stage_history.append({"event": "HALTED", **failure})
            if allow_return_to_stage3:
                self.run.current_stage = 3
                self.run.stage_history.append({"event": "RETURNED_TO_STAGE_3", **failure})
            else:
                self.run.status = "REJECTED"
            raise PipelineHalted(
                f"Stage {cur.number} ({cur.name}) gate failed: missing={missing} "
                f"criteria={[(e.criterion.id, e.passed) for e in evals]}"
            )

        self.run.stage_history.append(
            {"event": f"ENTERED_STAGE_{cur.number + 1}", "from": cur.number, "hypothesis": self.run.hypothesis_id}
        )
        self.run.current_stage += 1
        if self.run.current_stage > 15:
            self.run.current_stage = 15
            self.run.status = "COMPLETED"
        return self.run

    def goto(self, n: int) -> None:
        """Documented large rewind (e.g. hypothesis returned to Stage 3)."""
        if not (1 <= n <= 15):
            raise ValueError(f"Stage {n} out of the 1..15 pipeline.")
        self.run.stage_history.append({"event": f"JUMP_TO_STAGE_{n}", "from": self.run.current_stage})
        self.run.current_stage = n