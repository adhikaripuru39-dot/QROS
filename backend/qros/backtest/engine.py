"""Single-instrument event simulation; every signal executes on the next bar.

Bar ask prices are *modeled* as bid plus supplied spread, never represented as
observed ask history. Research only: bar paths and account conversion remain assumptions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Callable, Sequence


@dataclass(frozen=True)
class Bar:
    time: int
    open: float
    high: float
    low: float
    close: float
    spread: float  # Absolute price units, NOT MT5 points.


@dataclass(frozen=True)
class Signal:
    side: int  # 1 long, -1 short
    lots: float
    stop_distance: float
    take_distance: float


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10000
    contract_size: float = 100000
    leverage: float = 30
    commission_per_lot_side: float = 3.5
    slippage: float = 0  # Absolute price, always adverse, including stop fills.
    swap_per_lot_day: float = 0  # Account-currency debit per 24h (negative = credit).
    quote_to_account: float = 1  # Explicit constant conversion assumption.
    min_lot: float = .01
    lot_step: float = .01
    max_lot: float = 100
    liquidation_margin_level: float = .5
    slippage_per_lot: float = 0
    slippage_volatility_fraction: float = 0


@dataclass(frozen=True)
class Trade:
    entry_time: int
    exit_time: int
    side: int
    lots: float
    entry: float
    exit: float
    gross_pnl: float
    commission: float
    swap: float
    net_pnl: float
    reason: str


@dataclass
class BacktestResult:
    initial_cash: float
    final_cash: float
    trades: list[Trade] = field(default_factory=list)
    equity: list[tuple[int, float]] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    live_eligible: bool = False
    execution_evidence: str = "modeled_bar_path; no observed broker fill evidence"
    assumptions: list[str] = field(default_factory=lambda: [
        "Research simulation; not evidence of live fill quality or profitability",
        "Input OHLC must be bid prices; ask OHLC modeled with supplied constant per-bar spread",
        "Signals see completed bars only; entry at next open with adverse slippage",
        "Ambiguous bars choose stop before target; stop gaps filled at worse open",
        "Single position; opposing signals ignored until flat; final position closed at last close",
        "Margin uses entry notional/leverage; liquidation evaluated conservatively on adverse bar extreme",
        "Swap is explicit linear elapsed-day estimate; broker rollovers/triple swaps not modeled",
        "Quote-to-account conversion fixed; input must specify suitable account-currency conversion",
    ])

    @property
    def max_drawdown(self) -> float:
        peak, worst = self.initial_cash, 0.0
        for _, value in self.equity:
            peak = max(peak, value)
            worst = max(worst, (peak - value) / peak if peak > 0 else 1)
        return worst


class BacktestEngine:
    def run_ticks(self, bars, ticks, strategy, config=None, *, rollover=None, swap_records=(), cost_records=()):
        from .ticks import run_ticks
        return run_ticks(bars, ticks, strategy, config, rollover=rollover, swap_records=swap_records,cost_records=cost_records)

    def run(self, bars: Sequence[Bar], strategy: Callable[[tuple[Bar, ...]], Signal | None],
            config: BacktestConfig | None = None) -> BacktestResult:
        cfg = config or BacktestConfig()
        for key, value in vars(cfg).items():
            if not math.isfinite(value):
                raise ValueError(f"Nonfinite {key}")
        if min(cfg.initial_cash, cfg.contract_size, cfg.leverage, cfg.quote_to_account,
               cfg.min_lot, cfg.lot_step, cfg.max_lot) <= 0:
            raise ValueError("Positive account, contract, leverage and volume parameters required")
        if min(cfg.commission_per_lot_side, cfg.slippage, cfg.liquidation_margin_level,
               cfg.slippage_per_lot, cfg.slippage_volatility_fraction) < 0:
            raise ValueError("Costs and liquidation threshold cannot be negative")
        data = tuple(bars)
        for i, b in enumerate(data):
            if not all(math.isfinite(v) for v in vars(b).values()):
                raise ValueError("Nonfinite bar")
            if min(b.open, b.high, b.low, b.close) <= 0 or b.spread < 0:
                raise ValueError("Invalid prices or missing/negative spread")
            if b.high < max(b.open, b.close, b.low) or b.low > min(b.open, b.close, b.high):
                raise ValueError("Invalid OHLC")
            if i and b.time <= data[i-1].time:
                raise ValueError("Bars must be unique and strictly chronological")
        result = BacktestResult(cfg.initial_cash, cfg.initial_cash)
        cash, pending, position = cfg.initial_cash, None, None
        unit = cfg.contract_size * cfg.quote_to_account
        slip = cfg.slippage

        def close_position(b: Bar, exit_price: float, reason: str):
            nonlocal cash, position
            p = position
            gross = p["signal"].side * (exit_price - p["entry"]) * unit * p["signal"].lots
            commission = 2 * cfg.commission_per_lot_side * p["signal"].lots
            swap = max(0, b.time - p["time"]) / 86400 * cfg.swap_per_lot_day * p["signal"].lots
            net = gross - commission - swap
            cash += gross - commission / 2 - swap  # Entry commission already debited.
            result.trades.append(Trade(p["time"], b.time, p["signal"].side, p["signal"].lots,
                                       p["entry"], exit_price, gross, commission, swap, net, reason))
            position = None

        for i, b in enumerate(data):
            if position is None and pending is not None:
                s = pending
                if s.side not in (-1, 1) or not all(math.isfinite(v) for v in vars(s).values()) or min(s.lots, s.stop_distance, s.take_distance) <= 0:
                    raise ValueError("Invalid signal")
                volume_ok = (cfg.min_lot <= s.lots <= cfg.max_lot and
                             math.isclose(s.lots / cfg.lot_step, round(s.lots / cfg.lot_step), abs_tol=1e-7))
                prior_range = data[i-1].high - data[i-1].low if i else 0
                slip = cfg.slippage + cfg.slippage_per_lot*s.lots + cfg.slippage_volatility_fraction*prior_range
                entry = b.open + (b.spread if s.side == 1 else 0) + s.side * slip
                margin = entry * unit * s.lots / cfg.leverage
                entry_cost = cfg.commission_per_lot_side * s.lots
                immediate_loss = (b.spread + slip) * unit * s.lots
                if not volume_ok or margin + entry_cost + immediate_loss > cash:
                    result.rejected.append({"time": b.time, "reason": "volume" if not volume_ok else "insufficient_margin"})
                else:
                    cash -= entry_cost
                    position = {"signal": s, "entry": entry, "time": b.time, "margin": margin,
                                "stop": entry - s.side * s.stop_distance,
                                "take": entry + s.side * s.take_distance}
            pending = None
            if position is not None:
                p, s = position, position["signal"]
                offset = b.spread if s.side == -1 else 0
                op, lo, hi = b.open + offset, b.low + offset, b.high + offset
                adverse = lo if s.side == 1 else hi
                stop_hit = lo <= p["stop"] if s.side == 1 else hi >= p["stop"]
                take_hit = hi >= p["take"] if s.side == 1 else lo <= p["take"]
                swap = max(0, b.time - p["time"]) / 86400 * cfg.swap_per_lot_day * s.lots
                worst_equity = cash + s.side * (adverse - p["entry"]) * unit * s.lots - swap
                if stop_hit:
                    fill = min(op, p["stop"]) if s.side == 1 else max(op, p["stop"])
                    close_position(b, fill - s.side * slip, "stop")
                elif worst_equity <= p["margin"] * cfg.liquidation_margin_level:
                    close_position(b, adverse - s.side * slip, "margin_liquidation")
                elif take_hit:
                    close_position(b, p["take"] - s.side * slip, "target")
                elif i == len(data) - 1:
                    close_position(b, b.close + offset - s.side * slip, "end_of_data")
            equity = cash
            if position:
                s = position["signal"]
                mark = b.close + (b.spread if s.side == -1 else 0)
                swap = max(0, b.time - position["time"]) / 86400 * cfg.swap_per_lot_day * s.lots
                equity += s.side * (mark - position["entry"]) * unit * s.lots - swap - cfg.commission_per_lot_side * s.lots
            result.equity.append((b.time, equity))
            if position is None and i < len(data) - 1:
                pending = strategy(data[:i+1])
        result.final_cash = cash
        return result
