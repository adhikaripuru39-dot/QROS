"""Dataset Manifest and Registry management for immutable research tracking."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional
import yaml
from qros.tracking.lineage import get_git_commit_hash


@dataclass
class PartitionInfo:
    """Cryptographic and temporal metadata for a chronological partition."""

    tier_name: str
    bar_count: int
    percentage: float
    start_time_utc: str
    end_time_utc: str
    partition_sha256: str
    is_vaulted_oos: bool = False


@dataclass
class DatasetManifest:
    """Master cryptographic record for a registered research dataset."""

    dataset_id: str
    asset: str
    timeframe: str
    dataset_version: str
    total_bars: int
    calendar_span_years: float
    full_dataset_sha256: str
    partitions: Dict[str, PartitionInfo]
    source_metadata: Dict[str, Any]
    quality_approval_status: str
    git_commit_hash: str = "HEAD"
    date_registered_utc: str = ""

    def __post_init__(self) -> None:
        if not self.date_registered_utc:
            self.date_registered_utc = datetime.now(timezone.utc).isoformat()
        if self.git_commit_hash == "HEAD":
            self.git_commit_hash = get_git_commit_hash()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetManifest":
        data_copy = dict(data)
        if "partitions" in data_copy and isinstance(data_copy["partitions"], dict):
            part_map = {}
            for k, v in data_copy["partitions"].items():
                if isinstance(v, dict):
                    part_map[k] = PartitionInfo(**v)
                else:
                    part_map[k] = v
            data_copy["partitions"] = part_map
        return cls(**data_copy)

    @classmethod
    def from_json(cls, json_str: str) -> "DatasetManifest":
        data = json.loads(json_str)
        return cls.from_dict(data)


class DatasetRegistry:
    """Persistent registry tracking all approved datasets under docs/research/data/."""

    def __init__(self, registry_file: Optional[str] = None) -> None:
        if registry_file is None:
            base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs", "research", "data")
            )
            os.makedirs(base_dir, exist_ok=True)
            registry_file = os.path.join(base_dir, "DATASET_MANIFEST.json")

        self.registry_file = registry_file
        self.manifests: Dict[str, DatasetManifest] = self._load()

    def _load(self) -> Dict[str, DatasetManifest]:
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        return {k: DatasetManifest.from_dict(v) for k, v in raw.items()}
            except Exception:
                return {}
        return {}

    def register_dataset(self, manifest: DatasetManifest) -> None:
        """Add or update dataset manifest in registry and persist."""
        self.manifests[manifest.dataset_id] = manifest
        self.save()

    def save(self) -> None:
        """Persist registry to JSON file."""
        parent_dir = os.path.dirname(self.registry_file)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        data = {k: v.to_dict() for k, v in self.manifests.items()}
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_manifest(self, dataset_id: str) -> Optional[DatasetManifest]:
        """Retrieve manifest by dataset ID."""
        return self.manifests.get(dataset_id)
