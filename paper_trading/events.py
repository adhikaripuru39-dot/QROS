"""Event definitions for the QROS Micro-Engine Paper Trading System."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class BarEvent:
    """Emitted by MarketDataEngine when a new bar closes."""
    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread_pts: float = 20.0


@dataclass(frozen=True)
class SignalEvent:
    """Emitted by an individual Strategy Engine."""
    strategy_id: str
    symbol: str
    timestamp: str
    direction: int  # +1 for BUY, -1 for SELL, 0 for FLAT
    target_price: float
    stop_loss: float
    take_profit: float
    atr: float


@dataclass(frozen=True)
class AllocatedTargetEvent:
    """Emitted by PortfolioAllocatorEngine."""
    timestamp: str
    symbol: str
    strategy_targets: Dict[str, float]  # strategy_id -> target_lot_size (signed)


@dataclass(frozen=True)
class NetOrderEvent:
    """Emitted by PositionNettingEngine."""
    order_id: str
    timestamp: str
    symbol: str
    net_direction: int  # +1 for BUY, -1 for SELL, 0 for FLAT
    order_lots: float
    desired_total_lots: float
    stop_loss: float = 0.0
    take_profit: float = 0.0


@dataclass(frozen=True)
class RiskApprovedOrderEvent:
    """Emitted by RiskGuardEngine."""
    order_id: str
    timestamp: str
    symbol: str
    direction: int
    lots: float
    stop_loss: float = 0.0
    take_profit: float = 0.0
    is_approved: bool = False
    rejection_reason: Optional[str] = None


@dataclass(frozen=True)
class ExecutionFillEvent:
    """Emitted by ExecutionSimulatorEngine."""
    fill_id: str
    order_id: str
    timestamp: str
    symbol: str
    direction: int
    fill_price: float
    filled_lots: float
    spread_cost_usd: float
    slippage_cost_usd: float
    commission_usd: float
    realized_pnl_usd: float
    current_balance_usd: float
    current_equity_usd: float
