"""Tests for the 15-stage pipeline state machine (Part 7)."""

from __future__ import annotations

import pytest

from qros.hypothesis.mechanics import MECHANISM_CATALOG, documented_mechanisms
from qros.hypothesis.registry import HypothesisDoc
from qros.pipeline.gates import missing_artifacts
from qros.pipeline.stages import STAGES, all_stages, get_stage
from qros.pipeline.state_machine import PipelineHalted, ResearchPipeline


def _hyp(make_hyp_spec) -> HypothesisDoc:
    fields = make_hyp_spec("HYP-EQUITY-MICROSTRUCTURE-2026-0042")
    return HypothesisDoc(fields=fields, hypothesis_id=fields["HYP-01"])


def _advance_one(pipe: ResearchPipeline, stage: int, artifacts: list[str], **ctx) -> None:
    pipe.set_context(**ctx)
    for a in artifacts:
        pipe.present_artifact(stage, a)
    pipe.advance()


def test_fifteen_stages():
    assert len(all_stages()) == 15
    assert [s.number for s in STAGES] == list(range(1, 16))


def test_stage1_to_7_with_satisfied_gates(make_hyp_spec):
    pipe = ResearchPipeline(_hyp(make_hyp_spec))
    _advance_one(pipe, 1, ["idea_note", "mechanism_description"], qr_team_review=True)
    _advance_one(pipe, 2, ["annotated_bibliography", "academic_matrix"], edge_novelty_verified=True)
    _advance_one(pipe, 3, ["mechanism_spec"], head_of_research_mechanism_approved=True)
    _advance_one(pipe, 4, ["hyp_doc_locked"], hyp_sha256_locked=True, hyp_registered=True)
    _advance_one(pipe, 5, ["data_request", "schema_spec"], data_engineer_lineage_audit=True)
    assert pipe.stage() == 6


def test_stage7_refuses_bad_adf(make_hyp_spec):
    pipe = ResearchPipeline(_hyp(make_hyp_spec))
    # Reach stage 7 (feature engineering)
    for n, art, ctx in [
        (1, ["idea_note", "mechanism_description"], {"qr_team_review": True}),
        (2, ["annotated_bibliography", "academic_matrix"], {"edge_novelty_verified": True}),
        (3, ["mechanism_spec"], {"head_of_research_mechanism_approved": True}),
        (4, ["hyp_doc_locked"], {"hyp_sha256_locked": True, "hyp_registered": True}),
        (5, ["data_request", "schema_spec"], {"data_engineer_lineage_audit": True}),
        (6, ["cleansed_snapshot", "quality_metrics"], {"zero_bad_ticks": True, "timestamp_audit_pass": True}),
    ]:
        _advance_one(pipe, n, art, **ctx)
    # Stage 7 gate: max_adf_p must be < 0.05
    assert pipe.stage() == 7
    with pytest.raises(PipelineHalted):
        _advance_one(pipe, 7, ["feature_frame", "stationarity_metrics"], max_adf_p=0.12)
    assert pipe.run.status == "REJECTED"


def test_stage11_refuses_poor_oos(make_hyp_spec):
    pipe = ResearchPipeline(_hyp(make_hyp_spec))
    for n in range(1, 11):
        stage = get_stage(n)
        ctx = _gate_ctx(n)
        _advance_one(pipe, n, stage.outputs, **ctx)
    assert pipe.stage() == 11
    with pytest.raises(PipelineHalted):
        _advance_one(pipe, 11, ("walk_forward_matrix",), oos_sharpe=1.5, max_drawdown=0.10)


def _gate_ctx(stage: int) -> dict:
    """Provide satisfied context for each stage 1..10."""
    ctx = {
        1: {"qr_team_review": True},
        2: {"edge_novelty_verified": True},
        3: {"head_of_research_mechanism_approved": True},
        4: {"hyp_sha256_locked": True, "hyp_registered": True},
        5: {"data_engineer_lineage_audit": True},
        6: {"zero_bad_ticks": True, "timestamp_audit_pass": True},
        7: {"max_adf_p": 0.01},
        8: {"max_vif": 5.0},
        9: {"t_statistic": 4.0, "p_value": 0.0001},
        10: {"max_degradation_ratio": 0.20},
        11: {"oos_sharpe": 2.5, "max_drawdown": 0.08},
        12: {"corr_with_secondary": 0.9995},
        13: {"peer_review_signoff": True},
        14: {"ic_signoff": True},
        15: {"handoff_approved": True},
    }
    return ctx.get(stage, {})


def test_missing_artifact_blocks():
    from qros.hypothesis.registry import HypothesisDoc

    import qros.schemas.fields as fields_mod

    data = {f.id: "filled" for f in fields_mod.HYP_FIELDS}
    data["HYP-01"] = "HYP-2026-0001"
    hyp = HypothesisDoc(fields=data, hypothesis_id=data["HYP-01"])
    pipe = ResearchPipeline(hyp)
    # only 1 of 2 required artifacts produced
    pipe.present_artifact(1, "idea_note")
    assert missing_artifacts(get_stage(1), pipe._produced_for_current) == ["mechanism_description"]
    with pytest.raises(PipelineHalted):
        pipe.advance()


def test_goto_rewind_allowed(make_hyp_spec):
    pipe = ResearchPipeline(_hyp(make_hyp_spec))
    pipe.goto(3)
    assert pipe.stage() == 3


def test_mechanics_catalog_has_documented_six():
    assert len(documented_mechanisms()) == 6
    assert "MECH-01" in MECHANISM_CATALOG