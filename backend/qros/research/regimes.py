"""Trailing-window descriptors. These are estimators, not market truth."""
from __future__ import annotations
import math
from statistics import mean, pstdev
from collections.abc import Mapping
from datetime import datetime, timezone
from scipy.stats import jarque_bera


def value(bar, key, default=None):
    return bar.get(key, default) if isinstance(bar, Mapping) else getattr(bar, key, default)


def utc_time(bar):
    stamp = value(bar, "time", value(bar, "timestamp"))
    if isinstance(stamp, str):
        stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if isinstance(stamp, (int, float)):
        stamp = datetime.fromtimestamp(stamp, timezone.utc)
    if not isinstance(stamp, datetime) or stamp.tzinfo is None:
        raise ValueError("Bars require timezone-aware UTC timestamps")
    return stamp.astimezone(timezone.utc)


def characterize(bars, window=64, include_distribution=True):
    if window < 20:
        raise ValueError("At least 20 observations required")
    if len(bars) < window + 1:
        return {"available": False, "required": window + 1}
    tail = bars[-window-1:]
    c = [float(value(b, "close")) for b in tail]
    if any(x <= 0 or not math.isfinite(x) for x in c):
        raise ValueError("Invalid prices")
    r = [math.log(b/a) for a, b in zip(c, c[1:])]
    tr = [max(float(value(b,"high"))-float(value(b,"low")), abs(float(value(b,"high"))-prev), abs(float(value(b,"low"))-prev)) for b,prev in zip(tail[1:],c)]
    vol = pstdev(r)
    ewma = r[0] ** 2
    for x in r[1:]:
        ewma = .94 * ewma + .06 * x*x
    path = sum(abs(b-a) for a,b in zip(c,c[1:]))
    efficiency = abs(c[-1]-c[0])/path if path else 0.
    avg = mean(r)
    variance = sum((x-avg)**2 for x in r)
    ac = sum((a-avg)*(b-avg) for a,b in zip(r,r[1:]))/variance if variance else 0.
    # Rescaled-range Hurst descriptor is deliberately labelled a short-window proxy.
    walk, deviations = 0., []
    for x in r:
        walk += x-avg
        deviations.append(walk)
    rs = (max(deviations)-min(deviations))/vol if vol else 0.
    hurst = math.log(rs)/math.log(len(r)) if rs > 0 else None
    skew = mean([(x-avg)**3 for x in r])/vol**3 if vol else None
    kurt = mean([(x-avg)**4 for x in r])/vol**4 if vol else None
    # Wilder ADX smoothing over all supplied trailing bars.
    plus, minus = [], []
    for old,new in zip(tail,tail[1:]):
        up = float(value(new,"high"))-float(value(old,"high"))
        down = float(value(old,"low"))-float(value(new,"low"))
        plus.append(up if up>down and up>0 else 0.)
        minus.append(down if down>up and down>0 else 0.)
    st,sp,sm = sum(tr[:14]),sum(plus[:14]),sum(minus[:14])
    dx=[]
    for i in range(14,len(tr)):
        st,sp,sm = st-st/14+tr[i],sp-sp/14+plus[i],sm-sm/14+minus[i]
        dx.append(100*abs(sp-sm)/(sp+sm) if sp+sm else 0.)
    adx=mean(dx[:14]) if len(dx)>=14 else None
    for x in dx[14:]:
        adx=(13*adx+x)/14
    hour=utc_time(tail[-1]).hour
    rolling_atrs=[mean(tr[i-14:i]) for i in range(14,len(tr)+1)]
    session_profile={}
    for bar,ret in zip(tail[1:],r):
        stamp=utc_time(bar); h=stamp.hour
        name="asia" if h<7 else "london" if h<13 else "overlap" if h<17 else "new_york" if h<22 else "rollover"
        group=session_profile.setdefault(name,{"returns":[],"volumes":[]})
        group["returns"].append(ret); group["volumes"].append(float(value(bar,"tick_volume",0)))
    session_profile={name:{"observations":len(group["returns"]),"return_volatility":pstdev(group["returns"]),"mean_tick_volume":mean(group["volumes"])} for name,group in session_profile.items()}
    return {"available":True,"window":window,"ewma_volatility":math.sqrt(ewma),"realized_volatility":vol,
            "atr":mean(tr[-14:]),"atr_percentile":sum(x<=rolling_atrs[-1] for x in rolling_atrs)/len(rolling_atrs),
            "directional_efficiency":efficiency,"adx":adx,"hurst_rs_proxy":hurst,
            "regime":"trend" if efficiency>=.35 else "range", "volatility_regime":"high" if math.sqrt(ewma)>vol*1.2 else "normal",
            "session_utc":"asia" if hour<7 else "london" if hour<13 else "overlap" if hour<17 else "new_york" if hour<22 else "rollover",
            "skewness":skew,"pearson_kurtosis":kurt,"jarque_bera_pvalue":float(jarque_bera(r).pvalue) if vol and include_distribution else None,
            "return_autocorrelation_lag1":ac,"tick_volume_mean":mean(float(value(b,"tick_volume",0)) for b in tail[1:]),
            "session_profile_utc":session_profile,"session_profile_definition":"Fixed UTC descriptive buckets, not exchange hours"}
