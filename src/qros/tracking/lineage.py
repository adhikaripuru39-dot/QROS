"""Cryptographic experiment lineage and environment provenance capture."""

from dataclasses import asdict, dataclass
import json
import os
import platform
import subprocess
import sys
from typing import Any, Dict, Optional


@dataclass
class ExperimentLineage:
    """Provenance record capturing code version, system environment, dataset hash, and seeds."""

    git_commit_hash: str
    git_branch: str
    is_working_tree_dirty: bool
    python_version: str
    platform_system: str
    dataset_sha256: str
    random_seed: int
    validation_profile_name: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def get_git_commit_hash() -> str:
    """Retrieve current Git commit SHA hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def get_git_branch() -> str:
    """Retrieve current Git branch name."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_BRANCH"


def is_git_dirty() -> bool:
    """Check if Git working tree contains uncommitted changes."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return len(res.stdout.strip()) > 0
    except Exception:
        return False


def capture_lineage(
    dataset_sha256: str,
    random_seed: int = 42,
    validation_profile_name: str = "DEFAULT",
) -> ExperimentLineage:
    """Capture full cryptographic and runtime provenance metadata."""
    return ExperimentLineage(
        git_commit_hash=get_git_commit_hash(),
        git_branch=get_git_branch(),
        is_working_tree_dirty=is_git_dirty(),
        python_version=sys.version.split()[0],
        platform_system=f"{platform.system()} {platform.release()}",
        dataset_sha256=dataset_sha256,
        random_seed=random_seed,
        validation_profile_name=validation_profile_name,
    )
