"""Part 3 ch.2.2: Dataset Snapshot Registry — frozen, versioned, SHA-256 locked.

Research models NEVER query a dynamic database. They execute against frozen,
versioned Dataset Snapshots. ADR-002.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from qros.data.engineering import DatasetMetadata


class SnapshotLockedError(ValueError):
    """Raised when an operation would mutate a frozen snapshot."""


def _canonical_bytes(df: pd.DataFrame) -> bytes:
    """Deterministic canonical JSON of the DataFrame (stable offline, no pyarrow)."""
    canonical = df.copy()
    for col in canonical.columns:
        if pd.api.types.is_datetime64_any_dtype(canonical[col]):
            canonical[col] = canonical[col].astype(str)
        elif isinstance(canonical[col].dtype, pd.CategoricalDtype):
            canonical[col] = canonical[col].astype(str)
    payload = canonical.to_json(orient="split", date_format="iso")
    return json.dumps(json.loads(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass
class Snapshot:
    """A frozen, immutable dataset snapshot."""

    snapshot_id: str
    content: pd.DataFrame
    sha256: str
    metadata: DatasetMetadata


class SnapshotRegistry:
    """File-backed registry of frozen SHA-256-locked dataset snapshots."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.root / "manifests" / "snapshots.json"
        self._load_manifest()

    def _load_manifest(self) -> None:
        if self._manifest_path.exists():
            self._manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        else:
            self._manifest: dict[str, dict] = {}

    def _save_manifest(self) -> None:
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._manifest_path.write_text(
            json.dumps(self._manifest, indent=2, sort_keys=True), encoding="utf-8"
        )

    def register(self, body: pd.DataFrame, snapshot_id: str, metadata: DatasetMetadata) -> Snapshot:
        """Freeze a copy of ``body``, hash it, persist files, and record SHA-256.

        If ``snapshot_id`` already exists with a matching hash the registry is idempotent;
        a differing hash raises SnapshotLockedError (immutability).
        """
        frozen = body.copy(deep=True)
        raw_bytes = _canonical_bytes(frozen)
        digest = hashlib.sha256(raw_bytes).hexdigest()
        storage = self.root / "artifacts" / snapshot_id
        if storage.exists() and self._manifest.get(snapshot_id):
            if self._manifest[snapshot_id]["sha256"] != digest:
                raise SnapshotLockedError(
                    f"Cannot overwrite frozen snapshot {snapshot_id}: hash mismatch."
                )
            return Snapshot(snapshot_id, frozen, digest, metadata)
        storage.mkdir(parents=True, exist_ok=True)
        (storage / "data.canon").write_bytes(raw_bytes)
        (storage / "sha256.txt").write_text(digest, encoding="utf-8")
        self._manifest[snapshot_id] = {"sha256": digest, "path": str(storage)}
        self._save_manifest()
        return Snapshot(snapshot_id, frozen, digest, metadata)

    def get(self, snapshot_id: str, verify: bool = True) -> Snapshot:
        """Return a fresh frozen copy of the snapshot artifact."""
        if snapshot_id not in self._manifest:
            raise KeyError(f"No snapshot registered: {snapshot_id}")
        storage = self.root / "artifacts" / snapshot_id
        if verify and not self.verify(snapshot_id):
            raise SnapshotLockedError(f"Snapshot {snapshot_id} failed SHA-256 verification.")
        raw = (storage / "data.canon").read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        df = pd.DataFrame(payload["data"], columns=payload["columns"])
        meta = DatasetMetadata("", "", "", "")
        return Snapshot(snapshot_id, df, self._manifest[snapshot_id]["sha256"], meta)

    def list(self) -> list[str]:
        return sorted(self._manifest.keys())

    def verify(self, snapshot_id: str) -> bool:
        """Recompute the SHA-256 of the stored artifact; True only if it matches the record."""
        if snapshot_id not in self._manifest:
            return False
        try:
            raw = (self.root / "artifacts" / snapshot_id / "data.canon").read_bytes()
        except FileNotFoundError:
            return False
        return hashlib.sha256(raw).hexdigest() == self._manifest[snapshot_id]["sha256"]

    def all_frozen(self) -> bool:
        return all(self.verify(s) for s in self.list())