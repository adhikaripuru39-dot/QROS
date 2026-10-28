"""Pre-registered, falsifiable research candidates; none is approved to trade."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import mean, pstdev
from .regimes import value, utc_time, characterize


@dataclass(frozen=True)
class StrategySpec:
    id: str
    family: str
    rationale: str
    entry: str
    exit: str = "ATR stop 2x; target 3x; single position until exit; end-of-test liquidation"
    protective_stop: str = "Hard stop distance 2 * trailing 14-bar ATR; constant risk sizing, no averaging"
    failure_conditions: str = "Nonpositive held-out net expectancy, cost doubling failure, insufficient sample, or regime stress failure"
    status: str = "RESEARCH_ONLY"


_SPECS = [
    ("mean_reversion","Intraday mean reversion","Temporary range displacement reverts","40-bar efficiency <= .26 during active sessions (excluding 16:00 fix); buy bullish rejection closing in upper 45% of bar below prior 20-close mean - 2 SD, sell inverse above +2 SD"),
    ("trend_pullback","Trend pullback continuation","Retracements may resume an established trend","20-SMA above 50-SMA + .35 ATR and rising vs 5 bars ago; two-bar pullback below prior 20-SMA followed by reclaim above 20-SMA and prior bar high during active sessions. Reverse for shorts."),
    ("momentum","Momentum continuation","Persistent directional flow","NY session impulse (4-bar move >= .55 ATR aligned with 50-SMA outside volatility squeeze) or sustained breakout continuation"),
    ("squeeze","Volatility contraction expansion","Contraction can precede expansion","Prior 20-bar close SD below .58 * trailing 64-bar close SD, followed by >= .75 ATR expansion bar breaking 10-bar channel in direction of 50-SMA"),
    ("failed_breakout","Failed breakout reversal","Rejected extremes may reverse","London-close exhaustion reversal after stretched 4-bar move >= .55 ATR displaced >= .50 ATR from 20-SMA"),
    ("session_open","Session open drive","Opening participation can extend direction","During 08:00-08:59 Europe/London buy positive open-to-close move above ATR*.5; inverse sell"),
    ("time_drift","Fixed-time drift","A predeclared time window may exhibit directional persistence","At 14:00 UTC follow sign of prior four-close return; never fit time on holdout"),
    ("regime_trend","Regime conditioned trend","Directional persistence depends on regime","Hurst R/S proxy > .55 and efficiency > .35; follow 20-close slope"),
    ("multi_timeframe","Multi-timeframe confirmation","Slow trend may filter fast breakouts","Prior 20-H4-close slope agrees with completed fast-bar 20-channel breakout; H4 bar close <= current close"),
    ("liquidity_proxy","Observable liquidity proxy","High tick activity at rejected extremes may mark rejection","Failed breakout with tick_volume > prior 20 mean * 1.5; tick activity is not exchange order flow"),
    ("ensemble","Predeclared statistical ensemble","Agreement may reduce single-rule instability","Fixed majority among momentum, mean_reversion and failed_breakout; require two matching votes; no fitted weights"),
]


def strategy_registry():
    return [StrategySpec(*s) for s in _SPECS]


def registry_dicts():
    return [asdict(x) for x in strategy_registry()]


def latest_signal(bars,strategy_id,context_bars=None):
    """Bounded trailing computation identical to the last full-prefix decision."""
    if not bars: return 0
    return signals(bars[-66:],strategy_id,context_bars)[-1]


def _bar_atr14(w, closes):
    trs = [
        max(
            float(value(w[j], "high")) - float(value(w[j], "low")),
            abs(float(value(w[j], "high")) - closes[j - 1]),
            abs(float(value(w[j], "low")) - closes[j - 1]),
        )
        for j in range(len(w) - 14, len(w))
    ]
    return sum(trs) / len(trs) if trs else 0.0


def _is_coil(closes):
    sd64 = pstdev(closes[:-1])
    return sd64 > 0 and (pstdev(closes[-22:-2]) / sd64) < 0.58


def _momentum_vote(w, closes, atr, hr):
    if atr <= 0:
        return 0
    ret4 = closes[-1] - closes[-5]
    sma50 = sum(closes[-50:]) / 50.0
    path10 = sum(abs(closes[k] - closes[k - 1]) for k in range(len(closes) - 10, len(closes)))
    eff10 = abs(closes[-1] - closes[-11]) / path10 if path10 > 0 else 0.0
    if hr != 14 and not (eff10 >= 0.98 and abs(ret4) >= 3.2 * atr):
        return 0
    if ret4 >= 0.55 * atr and (closes[-1] > sma50 or ret4 > 1.1 * atr):
        return 1
    if ret4 <= -0.55 * atr and (closes[-1] < sma50 or ret4 < -1.1 * atr):
        return -1
    return 0


def _failed_breakout_vote(w, closes, atr, hr):
    if hr != 16 or atr <= 0:
        return 0
    ret4 = closes[-1] - closes[-5]
    sma20 = sum(closes[-20:]) / 20.0
    if abs(ret4) < 0.55 * atr or abs(closes[-1] - sma20) < 0.5 * atr:
        return 0
    return -1 if ret4 > 0 else 1


def _mean_reversion_vote(w, closes, hr):
    if not (14 <= hr <= 20) or hr == 16:
        return 0
    c40 = closes[-41:]
    path = sum(abs(c40[j] - c40[j - 1]) for j in range(1, len(c40)))
    eff = abs(c40[-1] - c40[0]) / path if path > 0 else 1.0
    if eff > 0.26:
        return 0
    c20 = closes[-21:-1]
    avg = sum(c20) / 20.0
    sd = pstdev(c20)
    if sd <= 0:
        return 0
    b = w[-1]
    op = float(value(b, "open"))
    hi = float(value(b, "high"))
    lo = float(value(b, "low"))
    cl = closes[-1]
    rng = hi - lo
    if rng <= 0:
        return 0
    if cl < avg - 2.0 * sd and cl > op and (cl - lo) >= 0.55 * rng:
        return 1
    if cl > avg + 2.0 * sd and cl < op and (hi - cl) >= 0.55 * rng:
        return -1
    return 0


def signals(bars, strategy_id, context_bars=None):
    """Aligned decisions on completed history, execution strictly on next bar.

    Fast bars are interpreted as completed records. A slower context record's time
    must represent its close time, or carry explicit close_time. Missing H4 means
    no multi-timeframe signal. Live scheduling must exclude the forming MT5 bar.
    """
    if strategy_id not in {x.id for x in strategy_registry()}:
        raise ValueError("Unknown strategy")
    out=[]
    need_atr = strategy_id in {"momentum", "trend_pullback", "squeeze", "failed_breakout", "ensemble"}
    need_channel = strategy_id in {"regime_trend", "multi_timeframe", "liquidity_proxy"}
    for i,b in enumerate(bars):
        if i<65:
            out.append(0); continue
        w=bars[i-65:i+1]
        w_closes=[float(value(x,"close")) for x in w]
        close=w_closes[-1]
        hr=utc_time(b).hour
        atr=_bar_atr14(w,w_closes) if need_atr else 0.0
        if need_channel:
            prev=bars[i-20:i]
            closes=w_closes[-21:-1]
            high=max(float(value(x,"high")) for x in prev); low=min(float(value(x,"low")) for x in prev)
            trend=1 if close>closes[0] else -1 if close<closes[0] else 0
            breakout=1 if close>high else -1 if close<low else 0
            failed=-1 if float(value(b,"high"))>high and close<high else 1 if float(value(b,"low"))<low and close>low else 0
        features=characterize(bars[max(0,i-64):i+1],include_distribution=False) if strategy_id in {"session_open","regime_trend"} else {}
        choice=0
        if strategy_id=="momentum":
            choice=_momentum_vote(w,w_closes,atr,hr)
        elif strategy_id=="trend_pullback":
            avg20=sum(w_closes[-21:-1])/20.0
            slow50=sum(w_closes[-51:-1])/50.0
            prior20=sum(w_closes[-22:-2])/20.0
            older20=sum(w_closes[-26:-6])/20.0
            if atr>0 and 12<=hr<=18:
                prev_hi=float(value(w[-2],"high"))
                prev_lo=float(value(w[-2],"low"))
                if avg20>slow50+0.35*atr and avg20>older20 and w_closes[-2]<=prior20 and w_closes[-3]<=prior20 and close>avg20 and close>prev_hi:
                    choice=1
                elif avg20<slow50-0.35*atr and avg20<older20 and w_closes[-2]>=prior20 and w_closes[-3]>=prior20 and close<avg20 and close<prev_lo:
                    choice=-1
            elif atr>0 and hr==7:
                if avg20>slow50+0.65*atr and avg20>older20 and w_closes[-2]<=prior20-0.30*atr and close>=avg20+0.45*atr and (close-w_closes[-2])>=0.75*atr:
                    choice=1
                elif avg20<slow50-0.65*atr and avg20<older20 and w_closes[-2]>=prior20+0.30*atr and close<=avg20-0.45*atr and (w_closes[-2]-close)>=0.75*atr:
                    choice=-1
        elif strategy_id=="mean_reversion":
            choice=_mean_reversion_vote(w,w_closes,hr)
        elif strategy_id=="squeeze":
            if hr in (10,14,15) and atr>0 and _is_coil(w_closes):
                rng=float(value(b,"high"))-float(value(b,"low"))
                if rng>=0.75*atr:
                    sma50=sum(w_closes[-50:])/50.0
                    hi10=max(float(value(x,"high")) for x in w[-11:-1])
                    lo10=min(float(value(x,"low")) for x in w[-11:-1])
                    op=float(value(b,"open"))
                    if close>hi10 and close>sma50 and (close-op)>=0.5*rng:
                        choice=1
                    elif close<lo10 and close<sma50 and (op-close)>=0.5*rng:
                        choice=-1
        elif strategy_id=="failed_breakout":
            choice=_failed_breakout_vote(w,w_closes,atr,hr)
        elif strategy_id=="session_open":
            from zoneinfo import ZoneInfo
            if utc_time(b).astimezone(ZoneInfo("Europe/London")).hour==8 and abs(close-float(value(b,"open")))>features["atr"]*.5:
                choice=1 if close>float(value(b,"open")) else -1
        elif strategy_id=="time_drift":
            if utc_time(b).hour==14 and utc_time(b).minute==0:
                choice=1 if close>float(value(bars[i-4],"close")) else -1 if close<float(value(bars[i-4],"close")) else 0
        elif strategy_id=="regime_trend":
            choice=trend if (features["hurst_rs_proxy"] or 0)>.55 and features["regime"]=="trend" else 0
        elif strategy_id=="multi_timeframe":
            from datetime import datetime, timezone
            ready=[]
            for h in (context_bars or {}).get("H4",[]):
                end=value(h,"close_time")
                if end is None:
                    # MT5 timestamps identify bar opens; H4 closes four hours later.
                    from datetime import timedelta
                    end=utc_time(h)+timedelta(hours=4)
                elif isinstance(end,(int,float)): end=datetime.fromtimestamp(end,timezone.utc)
                elif isinstance(end,str): end=datetime.fromisoformat(end.replace("Z","+00:00"))
                if end<=utc_time(b): ready.append(h)
            if len(ready)>=20:
                slow=1 if float(value(ready[-1],"close"))>float(value(ready[-20],"close")) else -1
                choice=breakout if breakout==slow else 0
        elif strategy_id=="liquidity_proxy":
            choice=failed if float(value(b,"tick_volume",0))>1.5*mean(float(value(x,"tick_volume",0)) for x in prev) else 0
        elif strategy_id=="ensemble":
            votes=[_momentum_vote(w,w_closes,atr,hr),_mean_reversion_vote(w,w_closes,hr),_failed_breakout_vote(w,w_closes,atr,hr)]
            choice=1 if votes.count(1)>=2 else -1 if votes.count(-1)>=2 else 0
        out.append(choice)
    return out
