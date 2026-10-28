"""Explicit selection policies, never an automatic live activation path."""
from __future__ import annotations
from statistics import mean

PROFILES = {
    "A":{"name":"High win rate","min_trades":100,"min_win_rate":.6,"max_win_rate":.8,"requires_hard_stops":True},
    "B":{"name":"Balanced execution","min_trades":100,"requires_hard_stops":True},
    "C":{"name":"Higher frequency","min_trades":200,"requires_hard_stops":True},
}


def profile_accepts(metrics,profile="B",hard_stops=True):
    if profile not in PROFILES: raise ValueError("Unknown selection profile")
    cfg=PROFILES[profile]
    if not metrics.get("available") or not hard_stops or metrics["n"]<cfg["min_trades"] or metrics["expectancy"]<=0: return False
    if profile=="A" and not cfg["min_win_rate"]<=metrics["win_rate"]<=cfg["max_win_rate"]: return False
    return True


def pareto_front(candidates):
    """Maximize expectancy, win rate and frequency; minimize drawdown."""
    keys=("expectancy","win_rate","frequency","max_drawdown")
    def vector(c): return [float(c[k])*(-1 if k=="max_drawdown" else 1) for k in keys]
    output=[]
    for candidate in candidates:
        v=vector(candidate)
        if not any(all(a>=b for a,b in zip(vector(other),v)) and any(a>b for a,b in zip(vector(other),v)) for other in candidates if other is not candidate):
            output.append(candidate)
    return output


def stress_gate(base, doubled_cost, regimes, min_regime_trades=20):
    failures=[]
    if not base or mean(base)<=0: failures.append("nonpositive_base_expectancy")
    if not doubled_cost or mean(doubled_cost)<=0: failures.append("doubled_execution_cost_failure")
    if len(regimes)<2: failures.append("insufficient_regime_coverage")
    for name,returns in regimes.items():
        if len(returns)<min_regime_trades: failures.append(f"regime_{name}_insufficient_sample")
        elif mean(returns)<=0: failures.append(f"regime_{name}_nonpositive_expectancy")
    return {"passed":not failures,"failures":failures,"min_regime_trades":min_regime_trades}
