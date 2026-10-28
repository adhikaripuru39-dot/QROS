"""Observed quote replay; never claims real broker fills from historical quotes."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import math
from .engine import BacktestConfig, BacktestResult, Trade


@dataclass(frozen=True)
class Tick:
    time_msc: int
    bid: float
    ask: float


@dataclass(frozen=True)
class RolloverSchedule:
    timezone: str = "UTC"
    hour: int = 22
    triple_weekday: int = 2
    long_debit_per_lot: float = 0
    short_debit_per_lot: float = 0

    def debit(self, entry_msc, exit_msc, side, lots):
        if not 0 <= self.hour <= 23 or not 0 <= self.triple_weekday <= 6:
            raise ValueError("Invalid broker rollover schedule")
        zone=ZoneInfo(self.timezone)
        start=datetime.fromtimestamp(entry_msc/1000,timezone.utc).astimezone(zone)
        end=datetime.fromtimestamp(exit_msc/1000,timezone.utc).astimezone(zone)
        day,debit=start.date(),0.
        rate=self.long_debit_per_lot if side==1 else self.short_debit_per_lot
        if not math.isfinite(rate): raise ValueError("Invalid swap rate")
        while day<=end.date():
            boundary=datetime(day.year,day.month,day.day,self.hour,tzinfo=zone)
            if start<boundary<=end and day.weekday()<5:
                debit+=rate*lots*(3 if day.weekday()==self.triple_weekday else 1)
            day+=timedelta(days=1)
        return debit


@dataclass(frozen=True)
class SwapRecord:
    time_msc: int
    debit_per_lot: float
    source: str


@dataclass(frozen=True)
class CostRecord:
    time_msc: int  # Earliest availability time of this sourced commission observation.
    commission_per_lot_side: float
    source: str


def run_ticks(bars,ticks,strategy,config=None,*,rollover=None,swap_records=(),cost_records=()):
    """Next-parent-bar entry at first observed quote. Final bar is a boundary sentinel.

    A sentinel prevents replay beyond the last proved parent boundary. To execute
    signals from the last real bar, append an explicitly known next boundary bar.
    Equal-millisecond quotes retain source order, never sorted or deduplicated.
    """
    cfg=config or BacktestConfig(); bars=tuple(bars); ticks=tuple(ticks)
    from .engine import BacktestEngine
    BacktestEngine().run(bars,lambda _:None,cfg)
    records=tuple(swap_records)
    costs=tuple(cost_records)
    if records and rollover is not None: raise ValueError("Choose observed swaps or modeled schedule")
    for r in records:
        if not r.source or not math.isfinite(r.debit_per_lot): raise ValueError("Sourced finite swap records required")
    if len({(r.time_msc,r.source) for r in records})!=len(records): raise ValueError("Duplicate swap records")
    for r in costs:
        if not r.source or not math.isfinite(r.commission_per_lot_side) or r.commission_per_lot_side<0:
            raise ValueError("Sourced nonnegative commission records required")
    if any(b.time_msc<=a.time_msc for a,b in zip(costs,costs[1:])):
        raise ValueError("Cost observations must have unique chronological availability times")
    for i,t in enumerate(ticks):
        if not all(math.isfinite(v) for v in (t.time_msc,t.bid,t.ask)) or t.bid<=0 or t.ask<t.bid:
            raise ValueError("Invalid observed quote")
        if i and t.time_msc<ticks[i-1].time_msc: raise ValueError("Ticks must retain chronological source order")
    result=BacktestResult(cfg.initial_cash,cfg.initial_cash)
    result.execution_evidence="observed_bid_ask_quotes; broker fills and depth unverified"
    result.assumptions=["Observed bid/ask quote sequence; same-millisecond source order retained",
        "Signals use completed parent bars only; final parent bar is a boundary sentinel",
        "Missing quote intervals have unknown paths; no quotes or fills synthesized",
        "Adverse slippage = base + lot-size coefficient + previous completed bar range coefficient",
        "Single position; fixed account conversion and simplified leverage margin",
        "Historical quotes do not establish broker fills, depth, latency or live eligibility",
        "Commission uses latest sourced observation available at event time, falling back to explicit config",
        "Financing uses sourced records" if records else "Financing uses configured broker rollover schedule" if rollover else "Financing uses elapsed-day estimate"]
    if len(bars)<3 or not ticks:
        result.rejected.append({"reason":"insufficient_parent_boundaries_or_observed_ticks"}); return result
    cash=cfg.initial_cash; position=None; cursor=0; unit=cfg.contract_size*cfg.quote_to_account

    def commission_rate(t):
        available=[r for r in costs if r.time_msc<=t.time_msc]
        return available[-1].commission_per_lot_side if available else cfg.commission_per_lot_side

    def swap(t):
        if position is None: return 0.
        p=position; s=p["signal"]
        if records: return sum(r.debit_per_lot*s.lots for r in records if p["time"]<r.time_msc<=t.time_msc)
        if rollover: return rollover.debit(p["time"],t.time_msc,s.side,s.lots)
        return max(0,t.time_msc-p["time"])/86400000*cfg.swap_per_lot_day*s.lots

    def close(t,reason):
        nonlocal position,cash
        p=position; s=p["signal"]
        price=(t.bid if s.side==1 else t.ask)-s.side*p["slip"]
        gross=s.side*(price-p["entry"])*unit*s.lots
        exit_commission=commission_rate(t)*s.lots
        commission=p["entry_commission"]+exit_commission; financing=swap(t)
        cash+=gross-exit_commission-financing
        result.trades.append(Trade(p["time"]/1000,t.time_msc/1000,s.side,s.lots,p["entry"],price,
                                  gross,commission,financing,gross-commission-financing,reason))
        position=None

    last_tick=None
    for i,b in enumerate(bars[:-1]):
        boundary=bars[i+1].time*1000
        while cursor<len(ticks) and ticks[cursor].time_msc<b.time*1000: cursor+=1
        segment_start=cursor
        while cursor<len(ticks) and ticks[cursor].time_msc<boundary: cursor+=1
        segment=ticks[segment_start:cursor]
        signal=strategy(bars[:i]) if i and position is None else None
        if signal is not None and not segment:
            result.rejected.append({"time":b.time,"reason":"missing_execution_quotes"})
        if signal is not None and segment:
            s=signal; t=segment[0]
            if s.side not in (-1,1) or not all(math.isfinite(v) for v in vars(s).values()) or min(s.lots,s.stop_distance,s.take_distance)<=0:
                raise ValueError("Invalid signal")
            volume_ok=cfg.min_lot<=s.lots<=cfg.max_lot and math.isclose(s.lots/cfg.lot_step,round(s.lots/cfg.lot_step),abs_tol=1e-7)
            slip=cfg.slippage+cfg.slippage_per_lot*s.lots+cfg.slippage_volatility_fraction*(bars[i-1].high-bars[i-1].low)
            entry=(t.ask if s.side==1 else t.bid)+s.side*slip
            margin=entry*unit*s.lots/cfg.leverage; cost=commission_rate(t)*s.lots
            if not volume_ok or margin+cost+(t.ask-t.bid+slip)*unit*s.lots>cash:
                result.rejected.append({"time":t.time_msc/1000,"reason":"volume" if not volume_ok else "insufficient_margin"})
            else:
                cash-=cost; position={"signal":s,"time":t.time_msc,"entry":entry,"margin":margin,
                                      "stop":entry-s.side*s.stop_distance,"take":entry+s.side*s.take_distance,"slip":slip,
                                      "entry_commission":cost}
        for t in segment:
            last_tick=t
            if position:
                p=position; s=p["signal"]; mark=t.bid if s.side==1 else t.ask
                equity=cash+s.side*(mark-p["entry"])*unit*s.lots-swap(t)-commission_rate(t)*s.lots
                if equity<=p["margin"]*cfg.liquidation_margin_level: close(t,"margin_liquidation")
                elif (mark<=p["stop"] if s.side==1 else mark>=p["stop"]): close(t,"stop")
                elif (mark>=p["take"] if s.side==1 else mark<=p["take"]): close(t,"target")
                result.equity.append((t.time_msc/1000,equity if position else cash))
            else: result.equity.append((t.time_msc/1000,cash))
    if position and last_tick:
        close(last_tick,"end_of_data")
        result.equity[-1]=(last_tick.time_msc/1000,cash)
    result.final_cash=cash
    return result
