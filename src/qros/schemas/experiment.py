"""Experiment schema and validation models enforcing QROS-STD-EXP-004."""

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any, Dict, List, Optional
import yaml


EXPERIMENT_ID_PATTERN = re.compile(r"^QROS-EXP-\d{6}$")


@dataclass
class ExperimentRecord:
    """Mandatory 19-Field Experiment Record Schema in accordance with QROS-STD-EXP-004."""

    # 1-2. Identifiers
    experiment_id: str
    hypothesis_id: str

    # 3-7. Dataset Lineage & Partitions
    dataset_version: str
    dataset_hash: str
    research_period: str
    training_period: str
    validation_period: str
    test_period: str

    # 8-12. Feature & Execution Specification
    feature_definitions: Dict[str, Any]
    signal_definition: str
    entry_execution_rules: str
    exit_execution_rules: str
    holding_period_stats: Dict[str, float]

    # 13-15. Cost & Sizing Configuration
    direct_costs_fees: Dict[str, float]
    slippage_assumptions: Dict[str, float]
    position_sizing_rules: str

    # 16-19. Evaluation, Tests & Conclusion
    evaluation_metrics: Dict[str, float]
    statistical_tests: Dict[str, Any]
    result_summary: Dict[str, Any]
    conclusion: str  # REJECTED, PROMISING, INCONCLUSIVE, CANDIDATE_PROMOTED

    # Metadata
    git_commit_hash: str = "HEAD"
    random_seed: int = 42
    author: str = "QROS Agent"
    date_executed: str = ""
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not EXPERIMENT_ID_PATTERN.match(self.experiment_id):
            raise ValueError(
                f"Invalid experiment_id: '{self.experiment_id}'. Must match pattern QROS-EXP-XXXXXX"
            )
        valid_conclusions = {
            "REJECTED",
            "PROMISING",
            "INCONCLUSIVE",
            "DATA INSUFFICIENT",
            "EXPERIMENT INVALID",
            "EDGE CANDIDATE ELIGIBLE",
            "CANDIDATE_PROMOTED",
            "PENDING",
        }
        if self.conclusion.upper() not in valid_conclusions:
            raise ValueError(
                f"Invalid conclusion: '{self.conclusion}'. Must be one of {valid_conclusions}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentRecord":
        return cls(**data)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "ExperimentRecord":
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ExperimentRecord":
        data = json.loads(json_str)
        return cls.from_dict(data)
