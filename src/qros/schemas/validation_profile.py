"""ValidationProfile configuration schema and default validation regime factories."""

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class ValidationProfile:
    """Declarative Validation Profile binding a research class to quantitative calibration parameters.

    In accordance with QROS-GOV-002, numerical parameters are initial default
    calibration baselines that can be fine-tuned or overridden for specific research designs.
    """

    class_id: str
    profile_name: str
    description: str = ""
    primary_frequency: str = "M5"
    typical_horizon: str = "< 2 Hours"
    min_trades: int = 400
    min_observations: int = 15000
    min_calendar_span_years: float = 3.0
    min_effective_trades: int = 200
    target_profit_factor: float = 1.35
    target_sharpe: float = 1.40
    dsr_hurdle: float = 0.95
    wfe_target: float = 0.65
    perturbation_grid: List[float] = field(default_factory=lambda: [0.15, 0.25])
    spread_multiplier: float = 2.0
    slippage_multiplier: float = 2.5
    latency_delay_ms: float = 200.0
    swap_financing: bool = False
    embargo_bars: int = 20
    default_oos_partition: float = 0.20
    custom_overrides: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        valid_classes = {
            "CLASS-I",
            "CLASS-II",
            "CLASS-III",
            "CLASS-IV",
            "CLASS-V",
            "CUSTOM",
        }
        if self.class_id.upper() not in valid_classes:
            raise ValueError(
                f"Invalid class_id: '{self.class_id}'. Must be one of {valid_classes}"
            )
        if self.min_trades <= 0:
            raise ValueError("min_trades must be positive")
        if not (0.0 < self.default_oos_partition < 1.0):
            raise ValueError("default_oos_partition must be strictly between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationProfile":
        """Construct profile from dictionary."""
        return cls(**data)

    def to_yaml(self) -> str:
        """Serialize profile to YAML string."""
        return yaml.dump(self.to_dict(), sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "ValidationProfile":
        """Deserialize profile from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    def to_json(self) -> str:
        """Serialize profile to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ValidationProfile":
        """Deserialize profile from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


def get_default_profile(class_id: str) -> ValidationProfile:
    """Factory creating the canonical default Validation Profile for a given Research Class.

    Parameters
    ----------
    class_id : str
        One of 'CLASS-I', 'CLASS-II', 'CLASS-III', 'CLASS-IV', 'CLASS-V'.

    Returns
    -------
    ValidationProfile
        The canonical default configuration object.
    """
    cid = class_id.upper().strip()

    if cid in ("CLASS-I", "CLASS-I: HF-MICRO", "CLASS_I"):
        return ValidationProfile(
            class_id="CLASS-I",
            profile_name="HF-MICRO_DEFAULT",
            description="High-Frequency & Intraday Microstructure Validation Regime",
            primary_frequency="Tick/M1/M5",
            typical_horizon="< 2 Hours",
            min_trades=1000,
            min_observations=50000,
            min_calendar_span_years=2.0,
            min_effective_trades=500,
            target_profit_factor=1.40,
            target_sharpe=1.80,
            dsr_hurdle=0.95,
            wfe_target=0.70,
            perturbation_grid=[0.10, 0.20],
            spread_multiplier=3.0,
            slippage_multiplier=4.0,
            latency_delay_ms=500.0,
            swap_financing=False,
            embargo_bars=50,
            default_oos_partition=0.20,
        )

    elif cid in ("CLASS-II", "CLASS-II: INTRADAY-MOM", "CLASS_II"):
        return ValidationProfile(
            class_id="CLASS-II",
            profile_name="INTRADAY-MOM_DEFAULT",
            description="Intraday Session & Momentum Validation Regime",
            primary_frequency="M5/M15/H1",
            typical_horizon="2 – 12 Hours",
            min_trades=400,
            min_observations=15000,
            min_calendar_span_years=3.0,
            min_effective_trades=200,
            target_profit_factor=1.35,
            target_sharpe=1.40,
            dsr_hurdle=0.95,
            wfe_target=0.65,
            perturbation_grid=[0.15, 0.25],
            spread_multiplier=2.0,
            slippage_multiplier=2.5,
            latency_delay_ms=200.0,
            swap_financing=False,
            embargo_bars=20,
            default_oos_partition=0.20,
        )

    elif cid in ("CLASS-III", "CLASS-III: SWING-STATARB", "CLASS_III"):
        return ValidationProfile(
            class_id="CLASS-III",
            profile_name="SWING-STATARB_DEFAULT",
            description="Swing & Multi-Day Statistical Arbitrage Validation Regime",
            primary_frequency="H1/H4/D1",
            typical_horizon="1 – 5 Days",
            min_trades=150,
            min_observations=5000,
            min_calendar_span_years=5.0,
            min_effective_trades=80,
            target_profit_factor=1.30,
            target_sharpe=1.20,
            dsr_hurdle=0.95,
            wfe_target=0.60,
            perturbation_grid=[0.20, 0.30],
            spread_multiplier=1.5,
            slippage_multiplier=2.0,
            latency_delay_ms=0.0,
            swap_financing=True,
            embargo_bars=10,
            default_oos_partition=0.20,
        )

    elif cid in ("CLASS-IV", "CLASS-IV: MACRO-REGIME", "CLASS_IV"):
        return ValidationProfile(
            class_id="CLASS-IV",
            profile_name="MACRO-REGIME_DEFAULT",
            description="Macro & Structural Regime Validation Regime",
            primary_frequency="D1/W1",
            typical_horizon="Weeks – Months",
            min_trades=40,
            min_observations=3000,
            min_calendar_span_years=12.0,
            min_effective_trades=30,
            target_profit_factor=1.50,
            target_sharpe=1.00,
            dsr_hurdle=0.90,
            wfe_target=0.55,
            perturbation_grid=[0.25, 0.40],
            spread_multiplier=1.5,
            slippage_multiplier=1.5,
            latency_delay_ms=0.0,
            swap_financing=True,
            embargo_bars=2,
            default_oos_partition=0.20,
        )

    elif cid in ("CLASS-V", "CLASS-V: CROSS-FACTOR", "CLASS_V"):
        return ValidationProfile(
            class_id="CLASS-V",
            profile_name="CROSS-FACTOR_DEFAULT",
            description="Cross-Sectional Panel Factor Relative Value Regime",
            primary_frequency="Panel Multi-Asset (M15/H1/D1)",
            typical_horizon="Hours – Weeks",
            min_trades=500,
            min_observations=10000,
            min_calendar_span_years=5.0,
            min_effective_trades=250,
            target_profit_factor=1.30,
            target_sharpe=1.30,
            dsr_hurdle=0.95,
            wfe_target=0.65,
            perturbation_grid=[0.15, 0.25],
            spread_multiplier=2.0,
            slippage_multiplier=2.5,
            latency_delay_ms=500.0,
            swap_financing=True,
            embargo_bars=20,
            default_oos_partition=0.20,
        )

    else:
        raise ValueError(
            f"Unknown class_id: '{class_id}'. Must be one of CLASS-I, CLASS-II, CLASS-III, CLASS-IV, CLASS-V."
        )
