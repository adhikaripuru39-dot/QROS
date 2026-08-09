"""Tests for tracking/experiment.py (Part 9)."""

from __future__ import annotations

import pytest

from qros.tracking.experiment import (
    ApprovalStatus,
    ExperimentRecord,
    ExperimentTracker,
    ReplicationStatus,
)


def test_exp_record_validates(make_exp_spec, tmp_path):
    tracker = ExperimentTracker(tmp_path / "track")
    rec = ExperimentRecord(**make_exp_spec())
    eid = tracker.log(rec)  # fills EXP-01 deterministically then validates
    saved = tracker.find(rec.hypothesis_id)[0]
    assert saved.validate() == []
    assert saved.experiment_id == eid == rec.experiment_id


def test_experiment_id_deterministic(make_exp_spec, tmp_path):
    tracker = ExperimentTracker(tmp_path / "track")
    a = ExperimentRecord(**make_exp_spec("HYP-2026-0001"))
    b = ExperimentRecord(**make_exp_spec("HYP-2026-0001"))
    id_a = tracker.log(a)
    id_b = tracker.log(b)
    assert id_a == id_b == a.experiment_id


def test_trial_count_increments(make_exp_spec, tmp_path):
    tracker = ExperimentTracker(tmp_path / "track")
    for i in range(3):
        spec = make_exp_spec("HYP-MULTI-2026-0001")
        spec["timestamp"] = f"2026-08-0{8 - i}T10:00:00Z"
        tracker.log(ExperimentRecord(**spec))
    assert tracker.trial_count("HYP-MULTI-2026-0001") == 3


def test_approve_and_reject(make_exp_spec, tmp_path):
    tracker = ExperimentTracker(tmp_path / "track")
    eid = tracker.log(ExperimentRecord(**make_exp_spec("HYP-2026-0002")))
    tracker.approve(eid)
    assert tracker.find("HYP-2026-0002")[0].approval_status == ApprovalStatus.APPROVED.value
    tracker.reject(eid, "not robust")
    assert tracker.find("HYP-2026-0002")[0].approval_status == ApprovalStatus.REJECTED.value


def test_status_enums():
    assert ApprovalStatus.APPROVED.value == "APPROVED"
    assert ReplicationStatus.NOT_VERIFIED.value == "NOT_VERIFIED"