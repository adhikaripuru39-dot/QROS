"""Configuration schemas.

Firm rules describe what the *prop firm* enforces. Internal limits describe the
stricter limits QROS applies to itself. Cross-validation prevents contradictory
configurations (e.g. an internal daily stop looser than the firm's daily loss).

All numeric example values shipped in config/ are EXAMPLES ONLY and must be
replaced with the actual firm's published rules before use.
"""
from __future__ import annotations

from datetime import time as WallTime
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FiniteModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class DrawdownType(str, Enum):
    STATIC = "static"                        # floor = initial - amount, never moves
    TRAILING_EOD = "trailing_eod"            # floor trails highest end-of-day balance
    TRAILING_INTRADAY = "trailing_intraday"  # floor trails highest observed equity


class DailyLossAnchor(str, Enum):
    START_OF_DAY_BALANCE = "start_of_day_balance"
    START_OF_DAY_EQUITY = "start_of_day_equity"
    START_OF_DAY_MAX = "start_of_day_max"  # max(balance, equity) at reset — most conservative


class AmountBasis(str, Enum):
    INITIAL_BALANCE = "initial_balance"
    ANCHOR = "anchor"  # percentage applied to the anchor value itself


class Measure(str, Enum):
    EQUITY = "equity"    # floating P/L counts (conservative, most firms)
    BALANCE = "balance"  # only closed P/L counts


class DailyLossRule(FiniteModel):
    pct: float = Field(gt=0, lt=100)
    anchor: DailyLossAnchor = DailyLossAnchor.START_OF_DAY_MAX
    amount_basis: AmountBasis = AmountBasis.INITIAL_BALANCE
    measure: Measure = Measure.EQUITY


class MaxLossRule(FiniteModel):
    pct: float = Field(gt=0, lt=100)
    drawdown_type: DrawdownType = DrawdownType.STATIC
    measure: Measure = Measure.EQUITY
    # Many trailing rules stop trailing once the floor reaches the initial balance.
    trail_lock_at_initial: bool = True


class DailyReset(FiniteModel):
    timezone: str = "Europe/Prague"
    time: WallTime = WallTime(0, 0)

    @field_validator("timezone")
    @classmethod
    def _tz_exists(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as e:  # pragma: no cover - message path
            raise ValueError(f"unknown timezone '{v}'") from e
        return v


class NewsRestriction(FiniteModel):
    enabled: bool = False
    minutes_before: int = Field(default=2, ge=0, le=240)
    minutes_after: int = Field(default=2, ge=0, le=240)
    flatten_before_news: bool = False
    cancel_pending_before_news: bool = False


class FirmProfile(FiniteModel):
    id: str = Field(pattern=r"^[a-z0-9_\-]+$")
    name: str
    is_example: bool = True
    currency: str = "USD"
    initial_balance: float = Field(gt=0)
    daily_loss: DailyLossRule
    max_loss: MaxLossRule
    daily_reset: DailyReset = DailyReset()
    profit_target_pct: Optional[float] = Field(default=None, gt=0, lt=1000)
    min_trading_days: int = Field(default=0, ge=0)
    # Max share of total profit allowed from a single day (e.g. 0.5 = 50%). None = no rule.
    consistency_max_day_share: Optional[float] = Field(default=None, gt=0, le=1)
    news: NewsRestriction = NewsRestriction()
    overnight_allowed: bool = True
    weekend_allowed: bool = False
    max_lots_per_order: Optional[float] = Field(default=None, gt=0)
    max_total_lots: Optional[float] = Field(default=None, gt=0)
    max_leverage: Optional[float] = Field(default=None, gt=0)
    automated_trading_allowed: bool = True
    commission_per_lot_round_turn: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def _consistency(self) -> "FirmProfile":
        if self.daily_loss.pct > self.max_loss.pct:
            raise ValueError("daily_loss.pct cannot exceed max_loss.pct")
        if (self.max_total_lots is not None and self.max_lots_per_order is not None
                and self.max_lots_per_order > self.max_total_lots):
            raise ValueError("max_lots_per_order cannot exceed max_total_lots")
        return self


class InternalLimits(FiniteModel):
    """QROS self-imposed limits. Always stricter than the firm."""

    risk_per_trade_pct: float = Field(default=0.25, gt=0, le=2.0)
    daily_warning_pct: float = Field(default=1.5, gt=0)
    daily_stop_pct: float = Field(default=2.0, gt=0)
    # Stop trading when total drawdown (vs. firm floor basis) reaches this pct of initial.
    total_stop_pct: float = Field(default=7.0, gt=0)
    max_open_positions: int = Field(default=3, ge=1, le=50)
    max_risk_per_instrument_pct: float = Field(default=0.5, gt=0)
    max_total_open_risk_pct: float = Field(default=1.0, gt=0)
    # Max aggregate risk in the same direction of any single currency (USD, EUR, XAU...).
    max_currency_risk_pct: float = Field(default=0.75, gt=0)
    max_session_loss_pct: float = Field(default=1.0, gt=0)
    max_trades_per_day: int = Field(default=12, ge=1, le=500)
    max_stale_quote_seconds: int = Field(default=10, ge=1, le=600)
    slippage_buffer_points: float = Field(default=5.0, ge=0)
    min_free_margin_pct: float = Field(default=50.0, ge=0, le=100)

    @model_validator(mode="after")
    def _order(self) -> "InternalLimits":
        if self.daily_warning_pct >= self.daily_stop_pct:
            raise ValueError("daily_warning_pct must be below daily_stop_pct")
        if self.risk_per_trade_pct > self.max_risk_per_instrument_pct:
            raise ValueError("risk_per_trade_pct cannot exceed max_risk_per_instrument_pct")
        if self.max_risk_per_instrument_pct > self.max_total_open_risk_pct:
            raise ValueError("max_risk_per_instrument_pct cannot exceed max_total_open_risk_pct")
        if self.max_total_open_risk_pct > self.daily_stop_pct:
            raise ValueError("max_total_open_risk_pct cannot exceed daily_stop_pct "
                             "(all open stops hit at once would breach the internal daily stop)")
        if self.max_session_loss_pct > self.daily_stop_pct:
            raise ValueError("max_session_loss_pct cannot exceed daily_stop_pct")
        return self


def cross_validate(firm: FirmProfile, limits: InternalLimits) -> list[str]:
    """Return a list of contradictions between firm rules and internal limits."""
    errors: list[str] = []
    if limits.daily_stop_pct >= firm.daily_loss.pct:
        errors.append(
            f"internal daily_stop_pct ({limits.daily_stop_pct}%) must be strictly below the "
            f"firm daily loss ({firm.daily_loss.pct}%)")
    if limits.total_stop_pct >= firm.max_loss.pct:
        errors.append(
            f"internal total_stop_pct ({limits.total_stop_pct}%) must be strictly below the "
            f"firm max loss ({firm.max_loss.pct}%)")
    if limits.max_total_open_risk_pct >= firm.daily_loss.pct:
        errors.append("max_total_open_risk_pct must be below the firm daily loss")
    return errors


class Session(FiniteModel):
    """A trading window in the firm timezone, e.g. 07:00-20:00."""
    start: WallTime
    end: WallTime
    days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon=0

    @field_validator("days")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        if not v or any(d < 0 or d > 6 for d in v):
            raise ValueError("days must be 0..6 and non-empty")
        return sorted(set(v))


class TradingHours(FiniteModel):
    timezone: str = "Europe/Prague"
    sessions: list[Session] = Field(default_factory=lambda: [Session(start=WallTime(8, 0), end=WallTime(20, 0))])
    flat_before_weekend_minutes: int = Field(default=30, ge=0)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        ZoneInfo(v)
        return v


class InstrumentConfig(FiniteModel):
    symbol: str
    enabled: bool = True
    asset_class: str = "fx"
    base: str
    quote: str
    max_spread_points: float = Field(gt=0)
    # Contract specs are DEFAULTS; live values must come from the broker (symbol_info).
    contract_size: float = Field(gt=0)
    tick_size: float = Field(gt=0)
    tick_value_per_lot: float = Field(gt=0, description="account-currency value of one tick per 1.0 lot")
    volume_min: float = Field(default=0.01, gt=0)
    volume_max: float = Field(default=50.0, gt=0)
    volume_step: float = Field(default=0.01, gt=0)
    min_stop_points: float = Field(default=0, ge=0)
    point: float = Field(gt=0)

    @model_validator(mode="after")
    def _vol(self) -> "InstrumentConfig":
        if self.volume_min > self.volume_max:
            raise ValueError("volume_min cannot exceed volume_max")
        return self


class TradingMode(str, Enum):
    OFF = "off"
    PAPER = "paper"
    DEMO = "demo"
    LIVE = "live"


class RunState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED_ENTRIES = "paused_entries"
    HALTED = "halted"  # risk limit / kill switch — requires explicit resume conditions

