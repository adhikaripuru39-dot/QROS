"""Part 9: Experiment Tracking System — 17-field Experiment Record."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

from qros.schemas.fields import EXP_ALL_IDS, EXP_FIELDS


class ApprovalStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReplicationStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    NOT_VERIFIED = "NOT_VERIFIED"
    VERIFIED = "VERIFIED"


@dataclass
class ExperimentRecord:
    """A 17-field institutional experiment record (EXP-01..EXP-17)."""

    experiment_id: str = ""
    timestamp: str = ""            # EXP-02 ISO 8601 UTC
    researcher: str = ""           # EXP-03
    dataset_hash: str = ""         # EXP-04
    code_commit: str = ""          # EXP-05
    feature_version: str = ""      # EXP-06
    hypothesis_id: str = ""        # EXP-07
    objective: str = ""            # EXP-08
    hyperparameters: dict = field(default_factory=dict)  # EXP-09
    test_output: dict = field(default_factory=dict)      # EXP-10 t/p/DSR/SR
    metrics: dict = field(default_factory=dict)          # EXP-11 IS/OOS SR, MaxDD, turnover
    conclusions: str = ""          # EXP-12
    limitations: str = ""          # EXP-13
    next_actions: str = ""         # EXP-14
    approval_status: str = ApprovalStatus.PENDING_REVIEW.value  # EXP-15
    peer_review_notes: str = ""    # EXP-16
    replication_status: str = ReplicationStatus.NOT_REQUIRED.value  # EXP-17

    def _as_fields(self) -> dict[str, str]:
        return {
            "EXP-01": self.experiment_id,
            "EXP-02": self.timestamp,
            "EXP-03": self.researcher,
            "EXP-04": self.dataset_hash,
            "EXP-05": self.code_commit,
            "EXP-06": self.feature_version,
            "EXP-07": self.hypothesis_id,
            "EXP-08": self.objective,
            "EXP-09": json.dumps(self.hyperparameters, sort_keys=True),
            "EXP-10": json.dumps(self.test_output, sort_keys=True),
            "EXP-11": json.dumps(self.metrics, sort_keys=True),
            "EXP-12": self.conclusions,
            "EXP-13": self.limitations,
            "EXP-14": self.next_actions,
            "EXP-15": self.approval_status,
            "EXP-16": self.peer_review_notes,
            "EXP-17": self.replication_status,
        }

    def validate(self) -> list[str]:
        errors = []
        for fdef in EXP_FIELDS:
            # EXP-16 (peer review notes) and EXP-17 (replication status) start empty
            if fdef.id in ("EXP-16", "EXP-17"):
                continue
            value = self._as_fields()[fdef.id]
            if value is None or str(value).strip() == "":
                errors.append(f"{fdef.id} ({fdef.name}) must be non-empty")
        if self.approval_status not in (ApprovalStatus.PENDING_REVIEW.value, ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value):
            errors.append("EXP-15 approval status invalid")
        return errors

    def to_canonical_json(self) -> str:
        return json.dumps(self._as_fields(), sort_keys=True, separators=(",", ":"))

    def generate_id(self) -> str:
        """Deterministic EXP id from hypothesis + timestamp + researcher (EXP-01)."""
        seed = f"{self.hypothesis_id}|{self.timestamp}|{self.researcher}"
        return "EXP-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8].upper()


class ExperimentTracker:
    """File-backed registry of experiment records; trial count feeds the DSR."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, exp_id: str) -> Path:
        return self.root / "experiments" / f"{exp_id}.json"

    def log(self, record: ExperimentRecord) -> str:
        """Persist a validated experiment record; returns its experiment_id."""
        if not record.experiment_id:
            record.experiment_id = record.generate_id()
        errors = record.validate()
        if errors:
            raise ValueError("; ".join(errors))
        p = self._path(record.experiment_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(record), indent=2, sort_keys=True), encoding="utf-8")
        return record.experiment_id

    def find(self, hyp_id: str) -> list[ExperimentRecord]:
        out = []
        for p in (self.root / "experiments").glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("hypothesis_id") == hyp_id:
                out.append(ExperimentRecord(**data))
        return sorted(out, key=lambda e: e.timestamp)

    def trial_count(self, hyp_id: str) -> int:
        """Total logged trials for a hypothesis — fed directly to the DSR (Part 9 ch.2)."""
        return len(self.find(hyp_id))

    def approve(self, exp_id: str) -> None:
        self._set_status(exp_id, ApprovalStatus.APPROVED.value)

    def reject(self, exp_id: str, note: str = "") -> None:
        data = self._load(exp_id)
        data["approval_status"] = ApprovalStatus.REJECTED.value
        if note:
            data["peer_review_notes"] = (data.get("peer_review_notes", "") + "\n" + note).strip()
        self._save(exp_id, data)

    def _load(self, exp_id: str) -> dict:
        p = self._path(exp_id)
        if not p.exists():
            raise KeyError(f"No experiment record: {exp_id}")
        return json.loads(p.read_text(encoding="utf-8"))

    def _save(self, exp_id: str, data: dict) -> None:
        self._path(exp_id).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    def _set_status(self, exp_id: str, status: str) -> None:
        data = self._load(exp_id)
        data["approval_status"] = status
        self._save(exp_id, data)