"""Part 5: Research Hypothesis Management — 22-field HYP registry with SHA-256 lock."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from qros.schemas.fields import HYP_ALL_IDS, HYP_FIELDS


class HypothesisValidationError(ValueError):
    """Raised when a hypothesis document fails the 22-field contract."""


class ImmutableLockError(RuntimeError):
    """Raised when a registered hypothesis has been tampered with."""


HYP_ID_PATTERN = re.compile(r"^HYP-[A-Z0-9-]+-\d{4}-\d{4}$")


@dataclass
class HypothesisDoc:
    """A registered Hypothesis Document (fields keyed by HYP-01..HYP-22)."""

    fields: dict[str, str]
    hypothesis_id: str = ""

    def __post_init__(self) -> None:
        if not self.hypothesis_id:
            self.hypothesis_id = self.fields.get("HYP-01", "")

    def validate(self) -> list[str]:
        """Return a list of errors; empty iff all 22 fields present and non-empty."""
        errors: list[str] = []
        missing = HYP_ALL_IDS - set(self.fields.keys())
        if missing:
            errors.append(f"Missing fields: {sorted(missing)}")
        if not HYP_ID_PATTERN.match(self.hypothesis_id):
            errors.append(f"HYP-01 is not a valid hypothesis id format: {self.hypothesis_id!r}")
        for fdef in HYP_FIELDS:
            value = self.fields.get(fdef.id, "")
            if value is None or str(value).strip() == "":
                errors.append(f"{fdef.id} ({fdef.name}) must be non-empty")
        return errors

    def require_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise HypothesisValidationError("; ".join(errors))

    def to_canonical_json(self) -> str:
        """Sorted-key canonical JSON (stable, deterministic)."""
        return json.dumps(self.fields, sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


class HypothesisRegistry:
    """File-backed registry; registration freezes the document with its SHA-256 lock."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _doc_path(self, hyp_id: str) -> Path:
        return self.root / "docs" / f"{hyp_id}.json"

    def _lock_path(self, hyp_id: str) -> Path:
        return self.root / "locks" / f"{hyp_id}.lock"

    def register(self, doc: HypothesisDoc) -> str:
        """Validate and register; returns the SHA-256 lock digest. Writes doc + lock."""
        doc.require_valid()
        digest = doc.sha256()
        doc_path = self._doc_path(doc.hypothesis_id)
        if doc_path.exists():
            # Already registered: idempotent only if the lock matches.
            if self._lock_path(doc.hypothesis_id).exists():
                stored = self.read_locked(doc.hypothesis_id)
                if stored.sha256() != digest:
                    raise ImmutableLockError(
                        f"HYP {doc.hypothesis_id} already registered with a different digest."
                    )
            return digest
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(doc.to_canonical_json(), encoding="utf-8")
        self._lock_path(doc.hypothesis_id).parent.mkdir(parents=True, exist_ok=True)
        self._lock_path(doc.hypothesis_id).write_text(digest, encoding="utf-8")
        return digest

    def lock(self, hyp_id: str, digest: str) -> str:
        """Explicitly record a lock digest for an id (used by CLI tooling)."""
        d = digest if len(digest) == 64 else ""
        if not d:
            raise ValueError("Lock digest must be a full SHA-256 hex string.")
        self._lock_path(hyp_id).parent.mkdir(parents=True, exist_ok=True)
        self._lock_path(hyp_id).write_text(d, encoding="utf-8")
        return d

    def read_locked(self, hyp_id: str) -> HypothesisDoc:
        doc_path = self._doc_path(hyp_id)
        if not doc_path.exists():
            raise KeyError(f"Hypothesis not registered: {hyp_id}")
        fields = json.loads(doc_path.read_text(encoding="utf-8"))
        # verify lock signature
        self.audit(hyp_id)
        return HypothesisDoc(fields=fields, hypothesis_id=hyp_id)

    def audit(self, hyp_id: str) -> bool:
        """Recompute the digest vs the stored lock; raise ImmutableLockError on tamper."""
        doc_path = self._doc_path(hyp_id)
        lock_path = self._lock_path(hyp_id)
        if not doc_path.exists() or not lock_path.exists():
            raise ImmutableLockError(f"Missing document or lock for {hyp_id}")
        fields = json.loads(doc_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        stored = lock_path.read_text(encoding="utf-8").strip()
        if digest != stored:
            raise ImmutableLockError(f"Hypothesis {hyp_id} tampered: digest mismatch (lock integrity violated).")
        return True

    def list(self) -> list[str]:
        docs = self.root / "docs"
        if not docs.exists():
            return []
        return sorted(p.stem for p in docs.glob("*.json"))

    def reject(self, hyp_id: str, reason: str, exp_ref: str = "") -> None:
        """Record a rejection per Part 7 failure protocol."""
        status_path = self.root / "status" / f"{hyp_id}.json"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "hypothesis_id": hyp_id,
            "status": "REJECTED",
            "reason": reason,
            "experiment_ref": exp_ref,
            "stage": "Part 7 gate failure protocol",
        }
        status_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")