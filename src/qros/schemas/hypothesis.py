"""Hypothesis schema and validation models enforcing QROS-STD-HYP-002."""

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any, Dict, Optional
import yaml
from qros.schemas.validation_profile import ValidationProfile, get_default_profile


HYPOTHESIS_ID_PATTERN = re.compile(r"^QROS-HYP-\d{6}$")


@dataclass
class HypothesisRecord:
    """Mandatory 18-Field Hypothesis Schema in accordance with QROS-STD-HYP-002."""

    # 1. Identifier
    hypothesis_id: str

    # 2-4. Asset & Market
    market: str
    asset: str
    timeframe: str

    # 5. Validation Regime / Profile
    research_class: str
    market_condition: str

    # 6-8. Theory & Proposition
    observation: str
    hypothesis_statement: str
    plausible_rationale: str

    # 9-11. State & Horizon Rules
    entry_condition: str
    exit_condition: str
    holding_period: str

    # 12-14. Statistical Target
    expected_effect: str
    null_hypothesis: str
    alternative_hypothesis: str

    # 15-17. Experimental Prerequisites
    required_data: str
    potential_confounders: str
    transaction_cost_assumptions: str

    # 18. Status & Lineage
    research_status: str = "REGISTERED"
    title: str = ""
    author: str = "QROS Researcher"
    date_created: str = ""
    validation_profile: Optional[ValidationProfile] = None
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate ID format
        if not HYPOTHESIS_ID_PATTERN.match(self.hypothesis_id):
            raise ValueError(
                f"Invalid hypothesis_id: '{self.hypothesis_id}'. Must match pattern QROS-HYP-XXXXXX (e.g. QROS-HYP-000001)"
            )

        # Attach default validation profile if not explicitly supplied
        if self.validation_profile is None:
            self.validation_profile = get_default_profile(self.research_class)

        # Verify required non-empty string fields
        required_str_fields = [
            ("market", self.market),
            ("asset", self.asset),
            ("timeframe", self.timeframe),
            ("observation", self.observation),
            ("hypothesis_statement", self.hypothesis_statement),
            ("plausible_rationale", self.plausible_rationale),
            ("entry_condition", self.entry_condition),
            ("exit_condition", self.exit_condition),
            ("null_hypothesis", self.null_hypothesis),
            ("alternative_hypothesis", self.alternative_hypothesis),
        ]
        for name, val in required_str_fields:
            if not val or not val.strip():
                raise ValueError(f"Hypothesis field '{name}' cannot be empty.")

    def validate_quality_standard(self) -> Dict[str, bool]:
        """Audit against the 6 Quality Gates of QROS-STD-HYP-002."""
        return {
            "specific": len(self.hypothesis_statement.strip()) >= 20,
            "falsifiable": (
                "H_0" in self.null_hypothesis or len(self.null_hypothesis) > 5
            ),
            "mechanically_testable": len(self.entry_condition.strip()) > 5
            and len(self.exit_condition.strip()) > 5,
            "time_bounded": len(self.holding_period.strip()) > 0,
            "condition_bounded": len(self.market_condition.strip()) > 0,
            "quantifiable": len(self.expected_effect.strip()) > 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.validation_profile:
            data["validation_profile"] = self.validation_profile.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HypothesisRecord":
        data_copy = dict(data)
        if "validation_profile" in data_copy and isinstance(
            data_copy["validation_profile"], dict
        ):
            data_copy["validation_profile"] = ValidationProfile.from_dict(
                data_copy["validation_profile"]
            )
        return cls(**data_copy)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "HypothesisRecord":
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
