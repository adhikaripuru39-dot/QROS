"""Strategy 3: Single Responsibility = Generate Signals for FVG Overlap Mitigations."""

from typing import List, Optional, Set
import pandas as pd
import numpy as np
from paper_trading.events import BarEvent, SignalEvent


class FVGOverlapStrategy:
    """QROS-HYP-000007: H1 Fair Value Gap Retests during London/NY Overlap (12:00-16:00 UTC)."""

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
            if not gap["mit"] and (bar.low <= gap["top"] and bar.high >= gap["bot"]):
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
            if not gap["mit"] and (bar.high >= gap["bot"] and bar.low <= gap["top"]):
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
