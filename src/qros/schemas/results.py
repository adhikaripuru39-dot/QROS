"""Statistical and validation results schema."""

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class BootstrapResult:
    """Non-parametric stationary bootstrap resampling result."""

    mean_sharpe: float
    ci_lower_95: float
    ci_upper_95: float
    n_resamples: int
    stationary_p: float
    ci_strictly_positive: bool


@dataclass
class DSRResult:
    """Deflated Sharpe Ratio calculation result per Bailey & López de Prado."""

    observed_sharpe: float
    benchmark_sharpe: float
    dsr_score: float
    trial_count_k: int
    sample_length_t: int
    skewness: float
    kurtosis: float
    is_statistically_significant: bool  # dsr_score >= hurdle


@dataclass
class StatisticalResult:
    """Comprehensive statistical verification result for a hypothesis or experiment."""

    hypothesis_id: str
    sample_size_n: int
    effective_sample_size_neff: float
    observation_count_t: int
    calendar_span_years: float

    # Moment statistics
    mean_return_net: float
    std_return_net: float
    skewness: float
    excess_kurtosis: float

    # Performance hurdles
    profit_factor_net: float
    annualized_sharpe_net: float
    annualized_sortino_net: float
    historical_var_99: float
    expected_shortfall_cvar_99: float
    t_statistic: float
    p_value: float

    # Advanced statistical models
    dsr_result: Optional[DSRResult] = None
    bootstrap_result: Optional[BootstrapResult] = None

    # Gate Evaluation against ValidationProfile
    passed_sample_power: bool = False
    passed_profit_factor: bool = False
    passed_sharpe: bool = False
    passed_dsr: bool = False
    passed_bootstrap_ci: bool = False
    overall_gate_pass: bool = False

    failure_reasons: List[str] = field(default_factory=list)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatisticalResult":
        data_copy = dict(data)
        if "dsr_result" in data_copy and isinstance(data_copy["dsr_result"], dict):
            data_copy["dsr_result"] = DSRResult(**data_copy["dsr_result"])
        if "bootstrap_result" in data_copy and isinstance(
            data_copy["bootstrap_result"], dict
        ):
            data_copy["bootstrap_result"] = BootstrapResult(
                **data_copy["bootstrap_result"]
            )
        return cls(**data_copy)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), sort_keys=False)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
