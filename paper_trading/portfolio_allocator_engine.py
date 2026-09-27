"""PortfolioAllocatorEngine: Single Responsibility = Allocate Strategy Risk Weights."""

from typing import Dict, Optional
from paper_trading.events import SignalEvent, AllocatedTargetEvent


class PortfolioAllocatorEngine:
    """Translates incoming strategy signals into dynamically sized target lots based on risk % and SL distance."""

    def __init__(
        self,
        risk_pct_per_trade: float = 0.02,  # 2% equity risk per trade
        contract_size: float = 100.0,      # 1 lot Gold = 100 oz ($100 per $1.00 move)
        min_lot: float = 0.01,
        max_lot: float = 3.0,
    ) -> None:
        self.risk_pct_per_trade = risk_pct_per_trade
        self.contract_size = contract_size
        self.min_lot = min_lot
        self.max_lot = max_lot
        self.current_strategy_targets: Dict[str, float] = {
            "STRAT_OB_ALLDAY": 0.0,
            "STRAT_OB_TREND": 0.0,
            "STRAT_FVG_OVERLAP": 0.0,
        }

    def calculate_lot_size(self, signal: SignalEvent, current_equity: float) -> float:
        """Calculates dynamic lot size = (Equity * Risk%) / (SL_Distance * ContractSize)."""
        if signal.direction == 0:
            return 0.0

        sl_dist = abs(signal.target_price - signal.stop_loss)
        if sl_dist <= 0 or current_equity <= 0:
            return self.min_lot

        risk_usd = current_equity * self.risk_pct_per_trade
        risk_per_lot_usd = sl_dist * self.contract_size
        computed_lots = risk_usd / risk_per_lot_usd

        # Clamp between min_lot and max_lot, rounded to 2 decimal places
        clamped_lots = max(self.min_lot, min(computed_lots, self.max_lot))
        return round(clamped_lots, 2)

    def on_signal(self, signal: SignalEvent, current_equity: float = 100_000.0) -> AllocatedTargetEvent:
        lot_size = self.calculate_lot_size(signal, current_equity)
        self.current_strategy_targets[signal.strategy_id] = float(signal.direction) * lot_size
        return AllocatedTargetEvent(
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            strategy_targets=dict(self.current_strategy_targets),
        )

    def close_strategy_position(self, strategy_id: str, timestamp: str, symbol: str) -> AllocatedTargetEvent:
        self.current_strategy_targets[strategy_id] = 0.0
        return AllocatedTargetEvent(
            timestamp=timestamp,
            symbol=symbol,
            strategy_targets=dict(self.current_strategy_targets),
        )
