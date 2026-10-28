"""Signals use completed bars only; this module never submits orders.

Call evaluate only for explicitly selected, lifecycle-approved strategies, then
pass its OrderIntent through the central risk gate. client_order_id is stable
across restarts/repeated evaluations and is the broker deduplication key.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import math
from typing import Mapping, Sequence

from qros.broker.base import Quote
from qros.risk.gate import ALLOWED_STATUS_BY_MODE, OrderIntent
from qros.risk.sizing import ContractSpec, size_position
from qros.config.schemas import TradingMode


@dataclass(frozen=True)
class Bar:
    """UTC-aware open timestamp and explicit duration, never an inferred close."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: float = 0


@dataclass(frozen=True)
class StrategyRuntime:
    strategy_id: str
    hypothesis_id: str
    symbol: str
    strategy_status: str
    timeframe_seconds: int
    risk_amount: float
    enabled: bool = False
    mode: TradingMode = TradingMode.PAPER
    atr_period: int = 14
    stop_atr_multiple: float = 2.0
    target_atr_multiple: float = 3.0
    commission_round_turn_per_lot: float = 0.0
    adverse_slippage_points: float = 0.0


@dataclass(frozen=True)
class SignalDecision:
    intent: OrderIntent | None
    client_order_id: str | None
    reason: str
    completed_bar_at: datetime | None = None


def completed_bars(bars: Sequence[Bar], duration: int, now: datetime):
    if duration <= 0 or now.tzinfo is None:
        raise ValueError('positive timeframe and aware clock required')
    result = []
    previous = None
    for b in bars:
        if b.time.tzinfo is None or (previous is not None and b.time <= previous):
            raise ValueError('bars must have unique ascending aware timestamps')
        previous = b.time
        prices = (b.open, b.high, b.low, b.close)
        if (any(not math.isfinite(v) or v <= 0 for v in prices)
                or not math.isfinite(b.tick_volume) or b.tick_volume < 0
                or b.low > min(b.open, b.close) or b.high < max(b.open, b.close) or b.low > b.high):
            raise ValueError('invalid OHLCV bar')
        end = b.time + timedelta(seconds=duration)
        if end <= now:
            # Registry decisions use completed timestamps; preserve explicit open.
            result.append({'time': end, 'open_time': b.time, 'close_time': end,
                           'open': b.open, 'high': b.high, 'low': b.low,
                           'close': b.close, 'tick_volume': b.tick_volume})
    return result


class SignalEngine:
    def __init__(self, max_quote_age_seconds=10, evaluator=None):
        self.max_quote_age_seconds = max_quote_age_seconds
        self.evaluator = evaluator

    def evaluate(self, strategy: StrategyRuntime, bars_by_timeframe: Mapping[int, Sequence[Bar]],
                 quote: Quote, now: datetime, spec: ContractSpec) -> SignalDecision:
        if not strategy.enabled:
            return SignalDecision(None, None, 'STRATEGY_DISABLED')
        if strategy.strategy_status not in ALLOWED_STATUS_BY_MODE.get(strategy.mode, set()):
            return SignalDecision(None, None, 'STRATEGY_STATUS_NOT_APPROVED')
        if (quote.symbol != strategy.symbol or spec.symbol != strategy.symbol or now.tzinfo is None
                or quote.time.tzinfo is None or not math.isfinite(quote.bid) or not math.isfinite(quote.ask)
                or not 0 < quote.bid <= quote.ask):
            return SignalDecision(None, None, 'INVALID_QUOTE_OR_SYMBOL')
        age = (now - quote.time).total_seconds()
        if not 0 <= age <= self.max_quote_age_seconds:
            return SignalDecision(None, None, 'QUOTE_STALE_OR_FUTURE')
        params = (strategy.risk_amount, strategy.stop_atr_multiple, strategy.target_atr_multiple,
                  strategy.commission_round_turn_per_lot, strategy.adverse_slippage_points)
        if (any(not math.isfinite(v) for v in params) or min(params[:3]) <= 0 or min(params[3:]) < 0
                or strategy.atr_period < 1):
            return SignalDecision(None, None, 'INVALID_STRATEGY_PARAMETERS')
        try:
            bars = completed_bars(bars_by_timeframe.get(strategy.timeframe_seconds, []),
                                  strategy.timeframe_seconds, now)
            context = {'H4': completed_bars(bars_by_timeframe.get(14400, []), 14400, now)}
        except ValueError:
            return SignalDecision(None, None, 'INVALID_BAR_DATA')
        if len(bars) < max(66, strategy.atr_period + 1):
            return SignalDecision(None, None, 'INSUFFICIENT_COMPLETED_HISTORY')
        end = bars[-1]['close_time']
        if (now - end).total_seconds() >= strategy.timeframe_seconds:
            return SignalDecision(None, None, 'BAR_FEED_STALE', end)
        # Gaps in the lookback invalidate the signal rather than implying continuity.
        lookback = max(66, strategy.atr_period + 1)
        window = bars[-lookback:]
        if any((right['time'] - left['time']).total_seconds() != strategy.timeframe_seconds
               for left, right in zip(window, window[1:])):
            return SignalDecision(None, None, 'BAR_HISTORY_GAP', end)
        if strategy.hypothesis_id == 'multi_timeframe' and len(context['H4']) < 20:
            return SignalDecision(None, None, 'INSUFFICIENT_COMPLETED_H4_HISTORY', end)
        if strategy.hypothesis_id == 'multi_timeframe':
            slow = context['H4'][-20:]
            if ((now - slow[-1]['time']).total_seconds() >= 14400
                    or any((b['time'] - a['time']).total_seconds() != 14400 for a, b in zip(slow, slow[1:]))):
                return SignalDecision(None, None, 'H4_FEED_STALE_OR_GAPPED', end)
        evaluator = self.evaluator
        if evaluator is None:
            from qros.research.registry import signals
            evaluator = signals
        try:
            decisions = evaluator(bars, strategy.hypothesis_id, context_bars=context)
        except (ValueError, KeyError, TypeError, ArithmeticError):
            return SignalDecision(None, None, 'HYPOTHESIS_EVALUATION_FAILED', end)
        if len(decisions) != len(bars) or decisions[-1] not in (-1, 0, 1):
            return SignalDecision(None, None, 'INVALID_HYPOTHESIS_OUTPUT', end)
        direction = decisions[-1]
        if not direction:
            return SignalDecision(None, None, 'NO_SIGNAL', end)
        history = bars[-(strategy.atr_period + 1):]
        atr = sum(max(b['high'] - b['low'], abs(b['high'] - previous['close']),
                      abs(b['low'] - previous['close'])) for previous, b in zip(history, history[1:])) / strategy.atr_period
        entry = quote.ask if direction == 1 else quote.bid
        stop = entry - direction * atr * strategy.stop_atr_multiple
        target = entry + direction * atr * strategy.target_atr_multiple
        sized = size_position(spec, strategy.risk_amount, entry, stop, spread=quote.ask - quote.bid,
                              slippage_points=strategy.adverse_slippage_points,
                              commission_per_lot=strategy.commission_round_turn_per_lot)
        if sized.rejected or stop <= 0 or target <= 0:
            return SignalDecision(None, None, 'SIZING_REJECTED:' + str(sized.reason), end)
        key = '|'.join([strategy.strategy_id, strategy.hypothesis_id, strategy.symbol,
                        str(strategy.timeframe_seconds), end.astimezone(timezone.utc).isoformat(),
                        str(direction)])
        cid = hashlib.sha256(key.encode()).hexdigest()[:24]
        intent = OrderIntent(strategy.symbol, 'buy' if direction == 1 else 'sell', entry, stop,
                             sized.volume, strategy.strategy_id, strategy.strategy_status, target)
        return SignalDecision(intent, cid, 'SIGNAL_REQUIRES_RISK_GATE', end)
