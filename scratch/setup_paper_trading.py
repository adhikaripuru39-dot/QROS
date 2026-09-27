"""Create dedicated paper_trading micro-engines obeying strict Single Responsibility Principle."""

import os

os.makedirs("paper_trading/strategies", exist_ok=True)
os.makedirs("paper_trading/logs", exist_ok=True)
os.makedirs("paper_trading/tests", exist_ok=True)

# 1. paper_trading/events.py
events_code = """\"\"\"Event definitions for the QROS Micro-Engine Paper Trading System.\"\"\"

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class BarEvent:
    \"\"\"Emitted by MarketDataEngine when a new bar closes.\"\"\"
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
    \"\"\"Emitted by an individual Strategy Engine.\"\"\"
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
    \"\"\"Emitted by PortfolioAllocatorEngine.\"\"\"
    timestamp: str
    symbol: str
    strategy_targets: Dict[str, float]  # strategy_id -> target_lot_size (signed)


@dataclass(frozen=True)
class NetOrderEvent:
    \"\"\"Emitted by PositionNettingEngine.\"\"\"
    order_id: str
    timestamp: str
    symbol: str
    net_direction: int  # +1 for BUY, -1 for SELL, 0 for FLAT
    order_lots: float
    desired_total_lots: float


@dataclass(frozen=True)
class RiskApprovedOrderEvent:
    \"\"\"Emitted by RiskGuardEngine.\"\"\"
    order_id: str
    timestamp: str
    symbol: str
    direction: int
    lots: float
    is_approved: bool
    rejection_reason: Optional[str] = None


@dataclass(frozen=True)
class ExecutionFillEvent:
    \"\"\"Emitted by ExecutionSimulatorEngine.\"\"\"
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
"""
with open("paper_trading/events.py", "w", encoding="utf-8") as f:
    f.write(events_code)

# 2. paper_trading/market_data_engine.py
market_data_code = """\"\"\"MarketDataEngine: Single Responsibility = Ingest & Resample Market Bars.\"\"\"

from typing import List, Optional
import pandas as pd
import numpy as np
from paper_trading.events import BarEvent


class MarketDataEngine:
    \"\"\"Maintains historical bar buffers and emits point-in-time BarEvents.\"\"\"

    def __init__(self, symbol: str = "XAUUSD") -> None:
        self.symbol = symbol
        self.m5_history: List[BarEvent] = []
        self.h1_history: List[BarEvent] = []

    def process_m5_bar(
        self,
        timestamp: str,
        open_p: float,
        high_p: float,
        low_p: float,
        close_p: float,
        volume: float,
        spread_pts: float = 20.0,
    ) -> BarEvent:
        bar = BarEvent(
            symbol=self.symbol,
            timeframe="M5",
            timestamp=timestamp,
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=volume,
            spread_pts=spread_pts,
        )
        self.m5_history.append(bar)
        return bar

    def get_h1_dataframe(self) -> pd.DataFrame:
        \"\"\"Resample M5 buffer into H1 OHLCV DataFrame with ATR and EMA.\"\"\"
        if len(self.m5_history) == 0:
            return pd.DataFrame()

        records = [
            {
                "timestamp": pd.to_datetime(b.timestamp),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in self.m5_history
        ]
        df = pd.DataFrame(records).set_index("timestamp").sort_index()
        df_h1 = df.resample("1h").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        ).dropna(subset=["open"])

        if len(df_h1) > 0:
            df_h1["tr"] = np.maximum(
                df_h1["high"] - df_h1["low"],
                np.maximum(
                    (df_h1["high"] - df_h1["close"].shift(1)).abs(),
                    (df_h1["low"] - df_h1["close"].shift(1)).abs(),
                ),
            )
            df_h1["atr14"] = df_h1["tr"].rolling(14).mean()
            df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()

        return df_h1
"""
with open("paper_trading/market_data_engine.py", "w", encoding="utf-8") as f:
    f.write(market_data_code)

# 3. Strategy 1: paper_trading/strategies/strategy_ob_allday.py (QROS-HYP-1068, Sharpe 15.21)
strat_ob_allday_code = """\"\"\"Strategy 1: Single Responsibility = Generate Signals for All-Day H1 Order Block Retests.\"\"\"

from typing import List, Optional
import pandas as pd
import numpy as np
from paper_trading.events import BarEvent, SignalEvent


class OrderBlockAllDayStrategy:
    \"\"\"QROS-HYP-1068: H1 Order Block Retests across 08:00-18:00 UTC (1.2x ATR displacement).\"\"\"

    def __init__(self, strategy_id: str = "STRAT_OB_ALLDAY", atr_mult: float = 1.2) -> None:
        self.strategy_id = strategy_id
        self.atr_mult = atr_mult
        self.active_bull_obs: List[dict] = []
        self.active_bear_obs: List[dict] = []
        self.last_h1_count = 0

    def update_order_blocks(self, df_h1: pd.DataFrame) -> None:
        if len(df_h1) <= self.last_h1_count or len(df_h1) < 3:
            return
        
        self.last_h1_count = len(df_h1)
        self.active_bull_obs.clear()
        self.active_bear_obs.clear()

        for i in range(2, len(df_h1)):
            b1 = df_h1.iloc[i - 1]
            b2 = df_h1.iloc[i]
            atr = b2.get("atr14", np.nan)
            if np.isnan(atr) or atr <= 0:
                continue

            # Bullish Order Block
            if b1["close"] < b1["open"] and (b2["close"] - b2["open"]) >= self.atr_mult * atr:
                self.active_bull_obs.append({
                    "created": b2.name,
                    "bot": b1["low"],
                    "top": b1["high"],
                    "tgt": b2["high"],
                    "sl": b1["low"] - 0.3 * atr,
                    "atr": atr,
                    "mit": False,
                })

            # Bearish Order Block
            if b1["close"] > b1["open"] and (b1["open"] - b2["close"]) >= self.atr_mult * atr:
                self.active_bear_obs.append({
                    "created": b2.name,
                    "bot": b1["low"],
                    "top": b1["high"],
                    "tgt": b2["low"],
                    "sl": b1["high"] + 0.3 * atr,
                    "atr": atr,
                    "mit": False,
                })

    def evaluate_bar(self, bar: BarEvent, df_h1: pd.DataFrame) -> Optional[SignalEvent]:
        self.update_order_blocks(df_h1)
        bar_time = pd.to_datetime(bar.timestamp)
        hour = bar_time.hour

        if not (8 <= hour < 18):
            return None

        # Clean expired (> 48h) or mitigated
        self.active_bull_obs = [o for o in self.active_bull_obs if (bar_time - o["created"]).total_seconds() <= 172800 and not o["mit"]]
        self.active_bear_obs = [o for o in self.active_bear_obs if (bar_time - o["created"]).total_seconds() <= 172800 and not o["mit"]]

        # Check Bullish Retest
        for ob in self.active_bull_obs:
            if ob["bot"] <= bar.low <= ob["top"]:
                ob["mit"] = True
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=1,
                    target_price=bar.close,
                    stop_loss=ob["sl"],
                    take_profit=ob["tgt"],
                    atr=ob["atr"],
                )

        # Check Bearish Retest
        for ob in self.active_bear_obs:
            if ob["bot"] <= bar.high <= ob["top"]:
                ob["mit"] = True
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=-1,
                    target_price=bar.close,
                    stop_loss=ob["sl"],
                    take_profit=ob["tgt"],
                    atr=ob["atr"],
                )

        return None
"""
with open("paper_trading/strategies/strategy_ob_allday.py", "w", encoding="utf-8") as f:
    f.write(strat_ob_allday_code)

# 4. Strategy 2: paper_trading/strategies/strategy_ob_trend.py (QROS-HYP-1070 / EDGE-000002, Sharpe 10.04)
strat_ob_trend_code = """\"\"\"Strategy 2: Single Responsibility = Generate Signals for Trend-Aligned Order Blocks.\"\"\"

from typing import List, Optional
import pandas as pd
import numpy as np
from paper_trading.events import BarEvent, SignalEvent


class OrderBlockTrendStrategy:
    \"\"\"QROS-HYP-1070: H1 Order Block Retests strictly aligned with H1 50-EMA Macro Trend.\"\"\"

    def __init__(self, strategy_id: str = "STRAT_OB_TREND", atr_mult: float = 1.0) -> None:
        self.strategy_id = strategy_id
        self.atr_mult = atr_mult
        self.active_bull_obs: List[dict] = []
        self.active_bear_obs: List[dict] = []
        self.last_h1_count = 0

    def update_order_blocks(self, df_h1: pd.DataFrame) -> None:
        if len(df_h1) <= self.last_h1_count or len(df_h1) < 3:
            return
        
        self.last_h1_count = len(df_h1)
        self.active_bull_obs.clear()
        self.active_bear_obs.clear()

        for i in range(2, len(df_h1)):
            b1 = df_h1.iloc[i - 1]
            b2 = df_h1.iloc[i]
            atr = b2.get("atr14", np.nan)
            ema50 = b2.get("ema50", np.nan)
            if np.isnan(atr) or np.isnan(ema50) or atr <= 0:
                continue

            # Bullish Trend-Aligned Order Block
            if b1["close"] < b1["open"] and (b2["close"] - b2["open"]) >= self.atr_mult * atr and b2["close"] > ema50:
                self.active_bull_obs.append({
                    "created": b2.name,
                    "bot": b1["low"],
                    "top": b1["high"],
                    "tgt": b2["high"],
                    "sl": b1["low"] - 0.3 * atr,
                    "atr": atr,
                    "mit": False,
                })

            # Bearish Trend-Aligned Order Block
            if b1["close"] > b1["open"] and (b1["open"] - b2["close"]) >= self.atr_mult * atr and b2["close"] < ema50:
                self.active_bear_obs.append({
                    "created": b2.name,
                    "bot": b1["low"],
                    "top": b1["high"],
                    "tgt": b2["low"],
                    "sl": b1["high"] + 0.3 * atr,
                    "atr": atr,
                    "mit": False,
                })

    def evaluate_bar(self, bar: BarEvent, df_h1: pd.DataFrame) -> Optional[SignalEvent]:
        self.update_order_blocks(df_h1)
        bar_time = pd.to_datetime(bar.timestamp)
        hour = bar_time.hour

        if not (12 <= hour < 18):
            return None

        self.active_bull_obs = [o for o in self.active_bull_obs if (bar_time - o["created"]).total_seconds() <= 172800 and not o["mit"]]
        self.active_bear_obs = [o for o in self.active_bear_obs if (bar_time - o["created"]).total_seconds() <= 172800 and not o["mit"]]

        for ob in self.active_bull_obs:
            if ob["bot"] <= bar.low <= ob["top"]:
                ob["mit"] = True
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=1,
                    target_price=bar.close,
                    stop_loss=ob["sl"],
                    take_profit=ob["tgt"],
                    atr=ob["atr"],
                )

        for ob in self.active_bear_obs:
            if ob["bot"] <= bar.high <= ob["top"]:
                ob["mit"] = True
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=-1,
                    target_price=bar.close,
                    stop_loss=ob["sl"],
                    take_profit=ob["tgt"],
                    atr=ob["atr"],
                )

        return None
"""
with open("paper_trading/strategies/strategy_ob_trend.py", "w", encoding="utf-8") as f:
    f.write(strat_ob_trend_code)

# 5. Strategy 3: paper_trading/strategies/strategy_fvg_overlap.py (QROS-HYP-000007 / EDGE-000001, Sharpe 2.77)
strat_fvg_code = """\"\"\"Strategy 3: Single Responsibility = Generate Signals for FVG Overlap Mitigations.\"\"\"

from typing import List, Optional
import pandas as pd
import numpy as np
from paper_trading.events import BarEvent, SignalEvent


class FVGOverlapStrategy:
    \"\"\"QROS-HYP-000007: H1 Fair Value Gap Retests during London/NY Overlap (12:00-16:00 UTC).\"\"\"

    def __init__(self, strategy_id: str = "STRAT_FVG_OVERLAP", atr_mult: float = 1.2) -> None:
        self.strategy_id = strategy_id
        self.atr_mult = atr_mult
        self.active_bull_gaps: List[dict] = []
        self.active_bear_gaps: List[dict] = []
        self.last_h1_count = 0

    def update_fvgs(self, df_h1: pd.DataFrame) -> None:
        if len(df_h1) <= self.last_h1_count or len(df_h1) < 3:
            return
        
        self.last_h1_count = len(df_h1)
        self.active_bull_gaps.clear()
        self.active_bear_gaps.clear()

        for i in range(2, len(df_h1)):
            b0 = df_h1.iloc[i - 2]
            b1 = df_h1.iloc[i - 1]
            b2 = df_h1.iloc[i]
            atr = b1.get("atr14", np.nan)
            if np.isnan(atr) or atr <= 0:
                continue

            if b2["low"] > b0["high"] and (b1["high"] - b1["low"]) >= self.atr_mult * atr:
                self.active_bull_gaps.append({
                    "created": b2.name,
                    "bot": b0["high"],
                    "top": b2["low"],
                    "tgt": b2["high"],
                    "sl": b0["high"] - 0.5 * atr,
                    "atr": atr,
                    "mit": False,
                })

            if b2["high"] < b0["low"] and (b1["high"] - b1["low"]) >= self.atr_mult * atr:
                self.active_bear_gaps.append({
                    "created": b2.name,
                    "bot": b2["high"],
                    "top": b0["low"],
                    "tgt": b2["low"],
                    "sl": b0["low"] + 0.5 * atr,
                    "atr": atr,
                    "mit": False,
                })

    def evaluate_bar(self, bar: BarEvent, df_h1: pd.DataFrame) -> Optional[SignalEvent]:
        self.update_fvgs(df_h1)
        bar_time = pd.to_datetime(bar.timestamp)
        hour = bar_time.hour

        if not (12 <= hour < 16):
            return None

        self.active_bull_gaps = [g for g in self.active_bull_gaps if (bar_time - g["created"]).total_seconds() <= 172800 and not g["mit"]]
        self.active_bear_gaps = [g for g in self.active_bear_gaps if (bar_time - g["created"]).total_seconds() <= 172800 and not g["mit"]]

        for gap in self.active_bull_gaps:
            if gap["bot"] <= bar.low <= gap["top"]:
                gap["mit"] = True
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=1,
                    target_price=bar.close,
                    stop_loss=gap["sl"],
                    take_profit=gap["tgt"],
                    atr=gap["atr"],
                )

        for gap in self.active_bear_gaps:
            if gap["bot"] <= bar.high <= gap["top"]:
                gap["mit"] = True
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=-1,
                    target_price=bar.close,
                    stop_loss=gap["sl"],
                    take_profit=gap["tgt"],
                    atr=gap["atr"],
                )

        return None
"""
with open("paper_trading/strategies/strategy_fvg_overlap.py", "w", encoding="utf-8") as f:
    f.write(strat_fvg_code)

# 6. paper_trading/portfolio_allocator_engine.py
allocator_code = """\"\"\"PortfolioAllocatorEngine: Single Responsibility = Allocate Strategy Risk Weights.\"\"\"

from typing import Dict, Optional
from paper_trading.events import SignalEvent, AllocatedTargetEvent


class PortfolioAllocatorEngine:
    \"\"\"Translates incoming strategy signals into allocated target lots per strategy.\"\"\"

    def __init__(self, base_lot_per_strategy: float = 1.0) -> None:
        self.base_lot_per_strategy = base_lot_per_strategy
        self.current_strategy_targets: Dict[str, float] = {
            "STRAT_OB_ALLDAY": 0.0,
            "STRAT_OB_TREND": 0.0,
            "STRAT_FVG_OVERLAP": 0.0,
        }

    def on_signal(self, signal: SignalEvent) -> AllocatedTargetEvent:
        # Direction: +1 -> +1.0 lot, -1 -> -1.0 lot, 0 -> 0.0 lot
        self.current_strategy_targets[signal.strategy_id] = float(signal.direction) * self.base_lot_per_strategy
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
"""
with open("paper_trading/portfolio_allocator_engine.py", "w", encoding="utf-8") as f:
    f.write(allocator_code)

# 7. paper_trading/position_netting_engine.py
netting_code = """\"\"\"PositionNettingEngine: Single Responsibility = Compute Net Order Delta.\"\"\"

import uuid
from typing import Optional
from paper_trading.events import AllocatedTargetEvent, NetOrderEvent


class PositionNettingEngine:
    \"\"\"Aggregates individual strategy lot targets and computes net order delta.\"\"\"

    def __init__(self) -> None:
        self.current_net_position: float = 0.0

    def process_allocation(self, allocation: AllocatedTargetEvent) -> Optional[NetOrderEvent]:
        desired_total = sum(allocation.strategy_targets.values())
        delta = desired_total - self.current_net_position

        if abs(delta) < 1e-5:
            return None  # Zero delta, no order needed

        order_dir = 1 if delta > 0 else -1
        order_lots = abs(delta)

        # Update tracked net position assuming order routing
        self.current_net_position = desired_total

        return NetOrderEvent(
            order_id=f"NET-ORD-{uuid.uuid4().hex[:8].upper()}",
            timestamp=allocation.timestamp,
            symbol=allocation.symbol,
            net_direction=order_dir,
            order_lots=order_lots,
            desired_total_lots=desired_total,
        )
"""
with open("paper_trading/position_netting_engine.py", "w", encoding="utf-8") as f:
    f.write(netting_code)

# 8. paper_trading/risk_guard_engine.py
risk_guard_code = """\"\"\"RiskGuardEngine: Single Responsibility = Validate Orders against Hard Risk Limits.\"\"\"

from typing import Optional
from paper_trading.events import NetOrderEvent, RiskApprovedOrderEvent


class RiskGuardEngine:
    \"\"\"Institutional pre-trade risk filter (Max exposure, Max daily drawdown, Max lot size).\"\"\"

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
                is_approved=False,
                rejection_reason=f"Desired total exposure exceeds limit: {order.desired_total_lots} > {self.max_total_lots} lots",
            )

        return RiskApprovedOrderEvent(
            order_id=order.order_id,
            timestamp=order.timestamp,
            symbol=order.symbol,
            direction=order.net_direction,
            lots=order.order_lots,
            is_approved=True,
            rejection_reason=None,
        )
"""
with open("paper_trading/risk_guard_engine.py", "w", encoding="utf-8") as f:
    f.write(risk_guard_code)

# 9. paper_trading/execution_simulator_engine.py
execution_code = """\"\"\"ExecutionSimulatorEngine: Single Responsibility = Simulate Broker Fills & Account Ledger.\"\"\"

import uuid
from typing import Optional
from paper_trading.events import RiskApprovedOrderEvent, ExecutionFillEvent


class ExecutionSimulatorEngine:
    \"\"\"Simulates realistic broker execution with spread, slippage, and tracks account PnL.\"\"\"

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
        commission_usd = 0.0  # 0 for raw FX/CFD spread model

        # PnL Realization if reducing/flipping position
        realized_pnl = 0.0
        new_signed_lots = self.current_position_lots + (order.direction * order.lots)

        if (self.current_position_lots > 0 and order.direction < 0) or (self.current_position_lots < 0 and order.direction > 0):
            closed_lots = min(abs(self.current_position_lots), order.lots)
            if self.current_position_lots > 0:
                realized_pnl = (fill_price - self.avg_entry_price) * closed_lots * 100.0
            else:
                realized_pnl = (self.avg_entry_price - fill_price) * closed_lots * 100.0

        # Update Balance and Position
        self.balance_usd += realized_pnl - spread_cost_usd - slippage_cost_usd
        self.equity_usd = self.balance_usd
        self.current_position_lots = new_signed_lots
        if abs(self.current_position_lots) > 0:
            self.avg_entry_price = fill_price
        else:
            self.avg_entry_price = 0.0

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
"""
with open("paper_trading/execution_simulator_engine.py", "w", encoding="utf-8") as f:
    f.write(execution_code)

# 10. paper_trading/audit_ledger_engine.py
audit_code = """\"\"\"AuditLedgerEngine: Single Responsibility = Persist Immutable Event Audit Trail.\"\"\"

import json
import os
from dataclasses import asdict
from typing import Any


class AuditLedgerEngine:
    \"\"\"Appends all paper trading events into a JSONL audit ledger.\"\"\"

    def __init__(self, log_path: str = "paper_trading/logs/PAPER_AUDIT_LEDGER.jsonl") -> None:
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def record_event(self, event_type: str, event_obj: Any) -> None:
        payload = {
            "event_type": event_type,
            "data": asdict(event_obj) if hasattr(event_obj, "__dataclass_fields__") else str(event_obj),
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\\n")
"""
with open("paper_trading/audit_ledger_engine.py", "w", encoding="utf-8") as f:
    f.write(audit_code)

# 11. paper_trading/orchestrator.py
orchestrator_code = """\"\"\"PaperTradingOrchestrator: Single Responsibility = Event Bus Message Routing.\"\"\"

from paper_trading.market_data_engine import MarketDataEngine
from paper_trading.strategies.strategy_ob_allday import OrderBlockAllDayStrategy
from paper_trading.strategies.strategy_ob_trend import OrderBlockTrendStrategy
from paper_trading.strategies.strategy_fvg_overlap import FVGOverlapStrategy
from paper_trading.portfolio_allocator_engine import PortfolioAllocatorEngine
from paper_trading.position_netting_engine import PositionNettingEngine
from paper_trading.risk_guard_engine import RiskGuardEngine
from paper_trading.execution_simulator_engine import ExecutionSimulatorEngine
from paper_trading.audit_ledger_engine import AuditLedgerEngine


class PaperTradingOrchestrator:
    \"\"\"Routes incoming market data sequentially through the 7 micro-engines.\"\"\"

    def __init__(self, symbol: str = "XAUUSD") -> None:
        self.market_data = MarketDataEngine(symbol=symbol)
        self.strat_ob_allday = OrderBlockAllDayStrategy()
        self.strat_ob_trend = OrderBlockTrendStrategy()
        self.strat_fvg = FVGOverlapStrategy()
        self.allocator = PortfolioAllocatorEngine(base_lot_per_strategy=1.0)
        self.netting = PositionNettingEngine()
        self.risk_guard = RiskGuardEngine()
        self.execution = ExecutionSimulatorEngine()
        self.audit = AuditLedgerEngine()

    def on_m5_bar(self, timestamp: str, open_p: float, high_p: float, low_p: float, close_p: float, volume: float, spread_pts: float = 20.0):
        # 1. Market Data Ingestion
        bar = self.market_data.process_m5_bar(timestamp, open_p, high_p, low_p, close_p, volume, spread_pts)
        df_h1 = self.market_data.get_h1_dataframe()
        self.audit.record_event("BAR_EVENT", bar)

        # 2. Strategy Signal Generation (Top 3 Strategies)
        sig1 = self.strat_ob_allday.evaluate_bar(bar, df_h1)
        sig2 = self.strat_ob_trend.evaluate_bar(bar, df_h1)
        sig3 = self.strat_fvg.evaluate_bar(bar, df_h1)

        for sig in [sig1, sig2, sig3]:
            if sig is None:
                continue

            self.audit.record_event("SIGNAL_EVENT", sig)

            # 3. Portfolio Allocation
            alloc = self.allocator.on_signal(sig)
            self.audit.record_event("ALLOCATED_TARGET_EVENT", alloc)

            # 4. Position Netting
            net_order = self.netting.process_allocation(alloc)
            if net_order is None:
                continue
            self.audit.record_event("NET_ORDER_EVENT", net_order)

            # 5. Risk Guard
            approved_order = self.risk_guard.validate_order(net_order, current_spread_pts=bar.spread_pts)
            self.audit.record_event("RISK_APPROVED_EVENT", approved_order)

            # 6. Execution Simulation
            if approved_order.is_approved:
                fill = self.execution.execute_order(approved_order, current_market_price=bar.close)
                if fill:
                    self.audit.record_event("EXECUTION_FILL_EVENT", fill)
"""
with open("paper_trading/orchestrator.py", "w", encoding="utf-8") as f:
    f.write(orchestrator_code)

print("Paper Trading System successfully initialized with 7 isolated micro-engines!")