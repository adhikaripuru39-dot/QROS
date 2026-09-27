"""Optimize active block list management in all 3 strategies."""

# 1. strategy_ob_allday.py
code1 = """\"\"\"Strategy 1: Single Responsibility = Generate Signals for All-Day H1 Order Block Retests.\"\"\"

from typing import List, Optional, Set
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
        self.mitigated_ids: Set[str] = set()
        self.last_h1_count = 0
        self.active_trade: Optional[dict] = None

    def update_order_blocks(self, df_h1: pd.DataFrame) -> None:
        if len(df_h1) <= self.last_h1_count or len(df_h1) < 3:
            return
        
        start_idx = max(2, self.last_h1_count)
        self.last_h1_count = len(df_h1)
        cutoff = df_h1.index[-1] - pd.Timedelta(hours=48)

        # Prune expired (> 48h) or already mitigated blocks
        self.active_bull_obs = [o for o in self.active_bull_obs if o["created"] >= cutoff and not o["mit"]]
        self.active_bear_obs = [o for o in self.active_bear_obs if o["created"] >= cutoff and not o["mit"]]

        for i in range(start_idx, len(df_h1)):
            b1 = df_h1.iloc[i - 1]
            b2 = df_h1.iloc[i]
            atr = b2.get("atr14", np.nan)
            if np.isnan(atr) or atr <= 0:
                continue

            block_id = f"{b2.name.isoformat()}"
            is_mitigated = block_id in self.mitigated_ids

            # Bullish Order Block
            if b1["close"] < b1["open"] and (b2["close"] - b2["open"]) >= self.atr_mult * atr:
                self.active_bull_obs.append({
                    "id": block_id,
                    "created": b2.name,
                    "bot": b1["low"],
                    "top": b1["high"],
                    "tgt": b2["high"],
                    "sl": b1["low"] - 0.3 * atr,
                    "atr": atr,
                    "mit": is_mitigated,
                })

            # Bearish Order Block
            if b1["close"] > b1["open"] and (b1["open"] - b2["close"]) >= self.atr_mult * atr:
                self.active_bear_obs.append({
                    "id": block_id,
                    "created": b2.name,
                    "bot": b1["low"],
                    "top": b1["high"],
                    "tgt": b2["low"],
                    "sl": b1["high"] + 0.3 * atr,
                    "atr": atr,
                    "mit": is_mitigated,
                })

    def evaluate_bar(self, bar: BarEvent, df_h1: pd.DataFrame) -> Optional[SignalEvent]:
        self.update_order_blocks(df_h1)
        bar_time = pd.to_datetime(bar.timestamp)
        hour = bar_time.hour

        # 1. Manage active trade lifecycle (TP / SL / Max 4h Holding Exit)
        if self.active_trade is not None:
            entry_time = self.active_trade["entry_time"]
            direction = self.active_trade["direction"]
            tp = self.active_trade["tp"]
            sl = self.active_trade["sl"]
            elapsed_sec = (bar_time - entry_time).total_seconds()

            should_exit = False
            if direction > 0:  # Long
                if bar.high >= tp or bar.low <= sl or elapsed_sec >= 14400:
                    should_exit = True
            else:  # Short
                if bar.low <= tp or bar.high >= sl or elapsed_sec >= 14400:
                    should_exit = True

            if should_exit:
                self.active_trade = None
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=0,  # FLAT
                    target_price=bar.close,
                    stop_loss=0.0,
                    take_profit=0.0,
                    atr=0.0,
                )
            return None

        # 2. Check for new entries during liquid hours (08:00 to 18:00 UTC)
        if not (8 <= hour < 18):
            return None

        for ob in self.active_bull_obs:
            if not ob["mit"] and ob["bot"] <= bar.low <= ob["top"]:
                ob["mit"] = True
                self.mitigated_ids.add(ob["id"])
                self.active_trade = {
                    "entry_time": bar_time,
                    "direction": 1,
                    "tp": ob["tgt"],
                    "sl": ob["sl"],
                }
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
            if not ob["mit"] and ob["bot"] <= bar.high <= ob["top"]:
                ob["mit"] = True
                self.mitigated_ids.add(ob["id"])
                self.active_trade = {
                    "entry_time": bar_time,
                    "direction": -1,
                    "tp": ob["tgt"],
                    "sl": ob["sl"],
                }
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
    f.write(code1)

# 2. strategy_ob_trend.py
code2 = """\"\"\"Strategy 2: Single Responsibility = Generate Signals for Trend-Aligned Order Blocks.\"\"\"

from typing import List, Optional, Set
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
        self.mitigated_ids: Set[str] = set()
        self.last_h1_count = 0
        self.active_trade: Optional[dict] = None

    def update_order_blocks(self, df_h1: pd.DataFrame) -> None:
        if len(df_h1) <= self.last_h1_count or len(df_h1) < 3:
            return
        
        start_idx = max(2, self.last_h1_count)
        self.last_h1_count = len(df_h1)
        cutoff = df_h1.index[-1] - pd.Timedelta(hours=48)

        # Prune expired (> 48h) or already mitigated blocks
        self.active_bull_obs = [o for o in self.active_bull_obs if o["created"] >= cutoff and not o["mit"]]
        self.active_bear_obs = [o for o in self.active_bear_obs if o["created"] >= cutoff and not o["mit"]]

        for i in range(start_idx, len(df_h1)):
            b1 = df_h1.iloc[i - 1]
            b2 = df_h1.iloc[i]
            atr = b2.get("atr14", np.nan)
            ema50 = b2.get("ema50", np.nan)
            if np.isnan(atr) or np.isnan(ema50) or atr <= 0:
                continue

            block_id = f"{b2.name.isoformat()}"
            is_mitigated = block_id in self.mitigated_ids

            # Bullish Trend-Aligned Order Block
            if b1["close"] < b1["open"] and (b2["close"] - b2["open"]) >= self.atr_mult * atr and b2["close"] > ema50:
                self.active_bull_obs.append({
                    "id": block_id,
                    "created": b2.name,
                    "bot": b1["low"],
                    "top": b1["high"],
                    "tgt": b2["high"],
                    "sl": b1["low"] - 0.3 * atr,
                    "atr": atr,
                    "mit": is_mitigated,
                })

            # Bearish Trend-Aligned Order Block
            if b1["close"] > b1["open"] and (b1["open"] - b2["close"]) >= self.atr_mult * atr and b2["close"] < ema50:
                self.active_bear_obs.append({
                    "id": block_id,
                    "created": b2.name,
                    "bot": b1["low"],
                    "top": b1["high"],
                    "tgt": b2["low"],
                    "sl": b1["high"] + 0.3 * atr,
                    "atr": atr,
                    "mit": is_mitigated,
                })

    def evaluate_bar(self, bar: BarEvent, df_h1: pd.DataFrame) -> Optional[SignalEvent]:
        self.update_order_blocks(df_h1)
        bar_time = pd.to_datetime(bar.timestamp)
        hour = bar_time.hour

        # 1. Manage active trade lifecycle
        if self.active_trade is not None:
            entry_time = self.active_trade["entry_time"]
            direction = self.active_trade["direction"]
            tp = self.active_trade["tp"]
            sl = self.active_trade["sl"]
            elapsed_sec = (bar_time - entry_time).total_seconds()

            should_exit = False
            if direction > 0:  # Long
                if bar.high >= tp or bar.low <= sl or elapsed_sec >= 14400:
                    should_exit = True
            else:  # Short
                if bar.low <= tp or bar.high >= sl or elapsed_sec >= 14400:
                    should_exit = True

            if should_exit:
                self.active_trade = None
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=0,
                    target_price=bar.close,
                    stop_loss=0.0,
                    take_profit=0.0,
                    atr=0.0,
                )
            return None

        # 2. Check for new entries during 12:00-18:00 UTC
        if not (12 <= hour < 18):
            return None

        for ob in self.active_bull_obs:
            if not ob["mit"] and ob["bot"] <= bar.low <= ob["top"]:
                ob["mit"] = True
                self.mitigated_ids.add(ob["id"])
                self.active_trade = {
                    "entry_time": bar_time,
                    "direction": 1,
                    "tp": ob["tgt"],
                    "sl": ob["sl"],
                }
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
            if not ob["mit"] and ob["bot"] <= bar.high <= ob["top"]:
                ob["mit"] = True
                self.mitigated_ids.add(ob["id"])
                self.active_trade = {
                    "entry_time": bar_time,
                    "direction": -1,
                    "tp": ob["tgt"],
                    "sl": ob["sl"],
                }
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
    f.write(code2)

# 3. strategy_fvg_overlap.py
code3 = """\"\"\"Strategy 3: Single Responsibility = Generate Signals for FVG Overlap Mitigations.\"\"\"

from typing import List, Optional, Set
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
        self.mitigated_ids: Set[str] = set()
        self.last_h1_count = 0
        self.active_trade: Optional[dict] = None

    def update_fvgs(self, df_h1: pd.DataFrame) -> None:
        if len(df_h1) <= self.last_h1_count or len(df_h1) < 3:
            return
        
        start_idx = max(2, self.last_h1_count)
        self.last_h1_count = len(df_h1)
        cutoff = df_h1.index[-1] - pd.Timedelta(hours=48)

        # Prune expired (> 48h) or already mitigated gaps
        self.active_bull_gaps = [g for g in self.active_bull_gaps if g["created"] >= cutoff and not g["mit"]]
        self.active_bear_gaps = [g for g in self.active_bear_gaps if g["created"] >= cutoff and not g["mit"]]

        for i in range(start_idx, len(df_h1)):
            b0 = df_h1.iloc[i - 2]
            b1 = df_h1.iloc[i - 1]
            b2 = df_h1.iloc[i]
            atr = b1.get("atr14", np.nan)
            if np.isnan(atr) or atr <= 0:
                continue

            gap_id = f"{b2.name.isoformat()}"
            is_mitigated = gap_id in self.mitigated_ids

            if b2["low"] > b0["high"] and (b1["high"] - b1["low"]) >= self.atr_mult * atr:
                self.active_bull_gaps.append({
                    "id": gap_id,
                    "created": b2.name,
                    "bot": b0["high"],
                    "top": b2["low"],
                    "tgt": b2["high"],
                    "sl": b0["high"] - 0.5 * atr,
                    "atr": atr,
                    "mit": is_mitigated,
                })

            if b2["high"] < b0["low"] and (b1["high"] - b1["low"]) >= self.atr_mult * atr:
                self.active_bear_gaps.append({
                    "id": gap_id,
                    "created": b2.name,
                    "bot": b2["high"],
                    "top": b0["low"],
                    "tgt": b2["low"],
                    "sl": b0["low"] + 0.5 * atr,
                    "atr": atr,
                    "mit": is_mitigated,
                })

    def evaluate_bar(self, bar: BarEvent, df_h1: pd.DataFrame) -> Optional[SignalEvent]:
        self.update_fvgs(df_h1)
        bar_time = pd.to_datetime(bar.timestamp)
        hour = bar_time.hour

        # 1. Manage active trade lifecycle
        if self.active_trade is not None:
            entry_time = self.active_trade["entry_time"]
            direction = self.active_trade["direction"]
            tp = self.active_trade["tp"]
            sl = self.active_trade["sl"]
            elapsed_sec = (bar_time - entry_time).total_seconds()

            should_exit = False
            if direction > 0:  # Long
                if bar.high >= tp or bar.low <= sl or elapsed_sec >= 14400:
                    should_exit = True
            else:  # Short
                if bar.low <= tp or bar.high >= sl or elapsed_sec >= 14400:
                    should_exit = True

            if should_exit:
                self.active_trade = None
                return SignalEvent(
                    strategy_id=self.strategy_id,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    direction=0,
                    target_price=bar.close,
                    stop_loss=0.0,
                    take_profit=0.0,
                    atr=0.0,
                )
            return None

        # 2. Check for new entries during 12:00-16:00 UTC
        if not (12 <= hour < 16):
            return None

        for gap in self.active_bull_gaps:
            if not gap["mit"] and gap["bot"] <= bar.low <= gap["top"]:
                gap["mit"] = True
                self.mitigated_ids.add(gap["id"])
                self.active_trade = {
                    "entry_time": bar_time,
                    "direction": 1,
                    "tp": gap["tgt"],
                    "sl": gap["sl"],
                }
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
            if not gap["mit"] and gap["bot"] <= bar.high <= gap["top"]:
                gap["mit"] = True
                self.mitigated_ids.add(gap["id"])
                self.active_trade = {
                    "entry_time": bar_time,
                    "direction": -1,
                    "tp": gap["tgt"],
                    "sl": gap["sl"],
                }
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
    f.write(code3)

print("Applied active list pruning optimization to all 3 strategies!")