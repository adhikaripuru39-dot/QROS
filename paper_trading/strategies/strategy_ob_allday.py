"""Strategy 1: Single Responsibility = Generate Signals for All-Day H1 Order Block Retests."""

from typing import List, Optional, Set
import pandas as pd
import numpy as np
from paper_trading.events import BarEvent, SignalEvent


class OrderBlockAllDayStrategy:
    """QROS-HYP-1068: H1 Order Block Retests across 08:00-18:00 UTC (1.2x ATR displacement)."""

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
            if not ob["mit"] and (bar.low <= ob["top"] and bar.high >= ob["bot"]):
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
            if not ob["mit"] and (bar.high >= ob["bot"] and bar.low <= ob["top"]):
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
