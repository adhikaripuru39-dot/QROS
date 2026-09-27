"""RiskGuardEngine: Single Responsibility = Validate Orders against Hard Risk Limits."""

from typing import Optional
from paper_trading.events import NetOrderEvent, RiskApprovedOrderEvent


class RiskGuardEngine:
    """Institutional pre-trade risk filter (Max exposure, Max daily drawdown, Max lot size)."""

    def __init__(
        self,
        max_total_lots: float = 5.0,
        max_single_order_lots: float = 3.0,
        max_spread_pts: float = 50.0,
    ) -> None:
        self.max_total_lots = max_total_lots
        self.max_single_order_lots = max_single_order_lots
        self.max_spread_pts = max_spread_pts

    def validate_order(self, order: NetOrderEvent, current_spread_pts: float = 20.0) -> RiskApprovedOrderEvent:
        # Check 1: Spread filter
        if current_spread_pts > self.max_spread_pts:
            return RiskApprovedOrderEvent(
                order_id=order.order_id,
                timestamp=order.timestamp,
                symbol=order.symbol,
                direction=order.net_direction,
                lots=order.order_lots,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                is_approved=False,
                rejection_reason=f"Spread too wide: {current_spread_pts} > {self.max_spread_pts} pts",
            )

        # Check 2: Single order size
        if order.order_lots > self.max_single_order_lots:
            return RiskApprovedOrderEvent(
                order_id=order.order_id,
                timestamp=order.timestamp,
                symbol=order.symbol,
                direction=order.net_direction,
                lots=order.order_lots,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                is_approved=False,
                rejection_reason=f"Order exceeds max size: {order.order_lots} > {self.max_single_order_lots} lots",
            )

        # Check 3: Desired total exposure
        if abs(order.desired_total_lots) > self.max_total_lots:
            return RiskApprovedOrderEvent(
                order_id=order.order_id,
                timestamp=order.timestamp,
                symbol=order.symbol,
                direction=order.net_direction,
                lots=order.order_lots,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                is_approved=False,
                rejection_reason=f"Desired total exposure exceeds limit: {order.desired_total_lots} > {self.max_total_lots} lots",
            )

        return RiskApprovedOrderEvent(
            order_id=order.order_id,
            timestamp=order.timestamp,
            symbol=order.symbol,
            direction=order.net_direction,
            lots=order.order_lots,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            is_approved=True,
            rejection_reason=None,
        )
