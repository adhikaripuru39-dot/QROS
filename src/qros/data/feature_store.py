"""Part 3 ch.2.3: Feature Store — central registry for online/offline features."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from qros.data.snapshot import SnapshotRegistry


@dataclass(frozen=True)
class FeatureSpec:
    """A declared feature with its documentation and validation contract."""

    name: str
    category: str
    expression: str
    owner: str
    # Part 4 / feature-statement gate checklist.
    documented: bool = True
    reproducible: bool = True
    no_lookahead: bool = True
    metadata_complete: bool = True
    validated: bool = True
    multi_regime: bool = True
    approved: bool = True

    def gate_checklist(self) -> dict[str, bool]:
        return {
            "documented": self.documented,
            "reproducible": self.reproducible,
            "no_lookahead": self.no_lookahead,
            "metadata_complete": self.metadata_complete,
            "validated": self.validated,
            "multi_regime": self.multi_regime,
            "approved": self.approved,
        }

    def passes_gate(self) -> bool:
        return all(self.gate_checklist().values())


class FeatureStore:
    """Registry of declared features and their frozen computed values by snapshot."""

    def __init__(self, root: Path, registry: SnapshotRegistry | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry = registry or SnapshotRegistry(self.root / "snapshots")
        self._defs_path = self.root / "feature_defs.json"
        self._defs: dict[str, FeatureSpec] = self._load_defs()

    def _load_defs(self) -> dict[str, FeatureSpec]:
        if not self._defs_path.exists():
            return {}
        raw = json.loads(self._defs_path.read_text(encoding="utf-8"))
        return {k: FeatureSpec(**v) for k, v in raw.items()}

    def _save_defs(self) -> None:
        self._defs_path.write_text(
            json.dumps({k: asdict(v) for k, v in self._defs.items()}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def define(self, name: str, category: str, expression: str, owner: str) -> FeatureSpec:
        spec = FeatureSpec(name=name, category=category, expression=expression, owner=owner)
        self._defs[name] = spec
        self._save_defs()
        return spec

    def put_feature(self, name: str, feature: pd.Series, snapshot_id: str) -> None:
        """Store the computed feature values against a frozen snapshot id."""
        if name not in self._defs:
            raise KeyError(f"Feature {name!r} not defined.")
        storage = self.root / "values" / name
        storage.mkdir(parents=True, exist_ok=True)
        payload = {
            "orientation": "columns",
            "index": [str(i) for i in feature.index],
            "columns": [name],
            "data": feature.tolist(),
            "attrs": {"snapshot_id": snapshot_id},
        }
        (storage / f"{snapshot_id}.json").write_text(json.dumps(payload), encoding="utf-8")

    def get(self, name: str, as_of_snapshot: str | None = None) -> pd.Series:
        """Return the stored feature series (optionally as-of a given snapshot)."""
        storage = self.root / "values" / name
        if not storage.exists():
            raise KeyError(f"No stored values for feature {name!r}.")
        files = sorted(storage.glob("*.json"))
        if as_of_snapshot:
            target = storage / f"{as_of_snapshot}.json"
            if not target.exists():
                raise KeyError(f"No values for {name!r} at snapshot {as_of_snapshot}.")
            files = [target]
        payload = json.loads(files[-1].read_text(encoding="utf-8"))
        index = pd.Index(payload["index"], name=name)
        data = payload["data"] if payload.get("orientation") == "columns" else np.array(payload["data"]).flatten()
        return pd.Series(data, index=index)