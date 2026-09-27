"""QROS Statistics package: moments, risk metrics, DSR, bootstrap, and multiple testing."""

from qros.stats.moments import (
    calculate_moments,
    calculate_profit_factor,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_var_cvar,
    calculate_effective_sample_size,
    calculate_t_stat,
)
from qros.stats.dsr import (
    calculate_dsr,
    calculate_psr,
    compute_expected_max_sharpe,
    calculate_sharpe_std_error,
)
from qros.stats.bootstrap import (
    StationaryBlockBootstrap,
    bootstrap_sharpe_ci,
)
from qros.stats.multiple_testing import (
    benjamini_hochberg,
    bonferroni_correction,
)

__all__ = [
    "calculate_moments",
    "calculate_profit_factor",
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
    "calculate_var_cvar",
    "calculate_effective_sample_size",
    "calculate_t_stat",
    "calculate_dsr",
    "calculate_psr",
    "compute_expected_max_sharpe",
    "calculate_sharpe_std_error",
    "StationaryBlockBootstrap",
    "bootstrap_sharpe_ci",
    "benjamini_hochberg",
    "bonferroni_correction",
]
