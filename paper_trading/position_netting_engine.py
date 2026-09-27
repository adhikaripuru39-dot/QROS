"""PositionNettingEngine: Single Responsibility = Compute Net Order Delta."""

import uuid
from typing import Optional
from paper_trading.events import AllocatedTargetEvent, NetOrderEvent, ExecutionFillEvent


class PositionNettingEngine:
    """Aggregates individual strategy lot targets and computes net order delta."""

    def __init__(self) -> None:
        self.current_net_position: float = 0.0

    def process_allocation(
        self, alloc: AllocatedTargetEvent, stop_loss: float = 0.0, take_profit: float = 0.0
    ) -> Optional[NetOrderEvent]:
        desired_total = sum(alloc.strategy_targets.values())
        delta = desired_total - self.current_net_position

        if abs(delta) < 1e-4:
            return None  # No position change needed

        direction = 1 if delta > 0 else -1
        order_lots = round(abs(delta), 2)

        return NetOrderEvent(
            order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            timestamp=alloc.timestamp,
            symbol=alloc.symbol,
            net_direction=direction,
            order_lots=order_lots,
            desired_total_lots=desired_total,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    def on_fill(self, fill: ExecutionFillEvent) -> None:
        """Two-Phase Commit: Update confirmed net position ONLY upon verified broker fill."""
        self.current_net_position += (fill.direction * fill.filled_lots)
