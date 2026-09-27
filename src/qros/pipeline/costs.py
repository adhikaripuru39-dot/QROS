"""Transaction cost and market friction modeling."""

from dataclasses import dataclass
from typing import Optional
import numpy as np
from qros.schemas.validation_profile import ValidationProfile


@dataclass
class CostModelConfig:
    """Base benchmark costs before stress multipliers."""

    base_spread_pts: float = 20.0  # e.g., 20 pts = $0.20 on XAUUSD, 2.0 pips on FX
    base_slippage_pts: float = 8.0  # nominal execution slippage
    commission_per_unit: float = 0.0  # fixed fee per standard lot / contract
    swap_long_daily_pts: float = 0.0  # financing rollover cost
    swap_short_daily_pts: float = 0.0
    point_value_multiplier: float = 1.0  # conversion from points to return basis


class TransactionCostModel:
    """Calculates realistic market friction deductions calibrated via a ValidationProfile."""

    def __init__(
        self,
        base_config: Optional[CostModelConfig] = None,
        profile: Optional[ValidationProfile] = None,
    ) -> None:
        self.config = base_config or CostModelConfig()
        self.profile = profile

    def calculate_total_friction_pts(
        self,
        is_stress_test: bool = False,
        holding_days: float = 0.0,
        is_long: bool = True,
    ) -> float:
        """Calculate total round-turn friction deduction in price points.

        Parameters
        ----------
        is_stress_test : bool
            Whether to apply the ValidationProfile's friction stress multipliers.
        holding_days : float
            Holding duration in days for swap/financing calculation.
        is_long : bool
            Trade direction for directional swap calculation.

        Returns
        -------
        float
            Total friction in points.
        """
        spread_mult = 1.0
        slippage_mult = 1.0
        latency_penalty_pts = 0.0

        if is_stress_test and self.profile is not None:
            spread_mult = self.profile.spread_multiplier
            slippage_mult = self.profile.slippage_multiplier
            if self.profile.latency_delay_ms > 0:
                # Approximate adverse tick drift from execution latency: 1 pt per 100ms
                latency_penalty_pts = (self.profile.latency_delay_ms / 100.0) * 1.5

        spread_pts = self.config.base_spread_pts * spread_mult
        slippage_pts = self.config.base_slippage_pts * slippage_mult

        # Swap financing
        swap_pts = 0.0
        if self.profile is None or self.profile.swap_financing:
            rate = self.config.swap_long_daily_pts if is_long else self.config.swap_short_daily_pts
            swap_pts = max(0.0, rate * holding_days)

        total_pts = spread_pts + slippage_pts + latency_penalty_pts + swap_pts
        return float(total_pts)

    def apply_friction_to_returns(
        self,
        gross_returns: np.ndarray,
        trade_duration_days: float = 0.0,
        is_stress_test: bool = False,
    ) -> np.ndarray:
        """Deduct transaction friction from a series of trade returns.

        Parameters
        ----------
        gross_returns : np.ndarray
            Array of gross trade return observations (in basis points or decimal return).
        trade_duration_days : float
            Average holding period in days.
        is_stress_test : bool
            Whether to apply stress multipliers.

        Returns
        -------
        np.ndarray
            Net returns after friction deduction.
        """
        arr = np.asarray(gross_returns, dtype=np.float64)
        friction_pts = self.calculate_total_friction_pts(
            is_stress_test=is_stress_test, holding_days=trade_duration_days
        )
        friction_return = friction_pts * self.config.point_value_multiplier

        net_returns = arr - friction_return
        return net_returns
