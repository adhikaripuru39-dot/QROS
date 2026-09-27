"""ExecutionSimulatorEngine: Single Responsibility = Simulate Broker Fills & Account Ledger."""

import uuid
from typing import Optional
from paper_trading.events import RiskApprovedOrderEvent, ExecutionFillEvent


class ExecutionSimulatorEngine:
    """Simulates realistic broker execution with spread, slippage, and tracks account PnL."""

    def __init__(
        self,
        starting_balance_usd: float = 100_000.0,
        spread_pts: float = 20.0,
        slippage_pts: float = 5.0,
    ) -> None:
        self.balance_usd: float = starting_balance_usd
        self.equity_usd: float = starting_balance_usd
        self.current_position_lots: float = 0.0
        self.avg_entry_price: float = 0.0
        self.spread_pts = spread_pts
        self.slippage_pts = slippage_pts

    def execute_order(self, order: RiskApprovedOrderEvent, current_market_price: float) -> Optional[ExecutionFillEvent]:
        if not order.is_approved or order.lots <= 0:
            return None

        # Calculate fill price with spread + slippage
        half_spread = (self.spread_pts * 0.01) / 2.0
        slippage = (self.slippage_pts * 0.01)

        if order.direction > 0:  # BUY
            fill_price = current_market_price + half_spread + slippage
        else:  # SELL
            fill_price = current_market_price - half_spread - slippage

        # Transaction friction costs in USD (1 lot of Gold = 100 oz)
        spread_cost_usd = (self.spread_pts * 0.01) * order.lots * 100.0
        slippage_cost_usd = slippage * order.lots * 100.0
        commission_usd = 0.0

        # PnL Realization if reducing/flipping position
        realized_pnl = 0.0
        prev_lots = self.current_position_lots
        new_signed_lots = prev_lots + (order.direction * order.lots)

        # 1. Closing or Reducing Position
        if (prev_lots > 0 and order.direction < 0) or (prev_lots < 0 and order.direction > 0):
            closed_lots = min(abs(prev_lots), order.lots)
            if prev_lots > 0:
                realized_pnl = (fill_price - self.avg_entry_price) * closed_lots * 100.0
            else:
                realized_pnl = (self.avg_entry_price - fill_price) * closed_lots * 100.0

        # 2. Updating Average Entry Price with VWAP
        if abs(new_signed_lots) < 1e-5:
            self.avg_entry_price = 0.0
        elif (prev_lots > 0 and order.direction > 0) or (prev_lots < 0 and order.direction < 0):
            # Adding in same direction -> Volume-Weighted Average Price (VWAP)
            total_notional = (abs(prev_lots) * self.avg_entry_price) + (order.lots * fill_price)
            self.avg_entry_price = total_notional / abs(new_signed_lots)
        elif (prev_lots == 0.0):
            # Fresh new position
            self.avg_entry_price = fill_price

        # Update Balance and Position
        self.balance_usd += (realized_pnl - spread_cost_usd - slippage_cost_usd)
        self.equity_usd = self.balance_usd
        self.current_position_lots = new_signed_lots

        return ExecutionFillEvent(
            fill_id=f"FILL-{uuid.uuid4().hex[:8].upper()}",
            order_id=order.order_id,
            timestamp=order.timestamp,
            symbol=order.symbol,
            direction=order.direction,
            fill_price=fill_price,
            filled_lots=order.lots,
            spread_cost_usd=spread_cost_usd,
            slippage_cost_usd=slippage_cost_usd,
            commission_usd=commission_usd,
            realized_pnl_usd=realized_pnl,
            current_balance_usd=self.balance_usd,
            current_equity_usd=self.equity_usd,
        )
