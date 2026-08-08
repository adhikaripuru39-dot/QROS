"""Part 2 1.6: Corporate Actions & Futures Instrument Rollovers.

- Corporate actions: point-in-time adjustment factors for splits and dividends.
- Futures rollovers: 4 continuous contract construction methodologies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    CASH_DIVIDEND = "CASH_DIVIDEND"


@dataclass(frozen=True)
class CorporateAction:
    """A corporate action with cross-vendor verification requirement."""

    action_id: str
    symbol: str
    action: ActionType
    factor: float
    vendors: int  # must be >= 2 for DE/DGO sign-off

    def verified_cross_vendor(self, min_vendors: int = 2) -> bool:
        """Part 1 4.2: split/dividend factors cross-validated against >= 2 vendors."""
        return self.vendors >= min_vendors


class RolloverMethod(str, Enum):
    OPEN_INTEREST = "open_interest"
    VOLUME = "volume"
    EXPIRATION_DATE = "expiration_date"
    RATIO_ADJUSTED_BACK = "ratio_adjusted_back"


ROLLOVER_METHODS: tuple[RolloverMethod, ...] = (
    RolloverMethod.OPEN_INTEREST,
    RolloverMethod.VOLUME,
    RolloverMethod.EXPIRATION_DATE,
    RolloverMethod.RATIO_ADJUSTED_BACK,
)


def validate_factor_cross_vendor(factors: dict[str, float]) -> bool:
    """Return True if all reported adjustment factors agree to 1e-9 tolerance."""
    if len(factors) < 2:
        return False
    values = list(factors.values())
    base = values[0]
    return all(abs(v - base) <= 1e-9 for v in values[1:])