"""Bailey/Lopez de Prado PSR/DSR, with explicit IID assumptions.

Source: https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
All Sharpes are unannualized and require comparable observation horizons.
Trade-return statistics do not establish independence or live profitability.
"""
from __future__ import annotations
import math
import random
from statistics import mean, stdev, pstdev
from scipy.stats import norm, t, ttest_ind
from qros.reporting.stats import wilson_interval, max_drawdown


def finite_sample(xs):
    values=[float(x) for x in xs]
    if any(not math.isfinite(x) for x in values):
        raise ValueError("Nonfinite observations")
    return values


def sharpe(xs):
    xs=finite_sample(xs)
    return mean(xs)/stdev(xs) if len(xs)>1 and stdev(xs)>0 else None


def probabilistic_sharpe(xs, benchmark=0.):
    xs=finite_sample(xs); sr=sharpe(xs)
    if sr is None or len(xs)<4: return None
    center=mean(xs); sd=pstdev(xs)
    skew=mean([(x-center)**3 for x in xs])/sd**3
    kurt=mean([(x-center)**4 for x in xs])/sd**4
    variance=1-skew*sr+(kurt-1)*sr*sr/4
    if variance<=0: return None
    return float(norm.cdf((sr-benchmark)*math.sqrt(len(xs)-1)/math.sqrt(variance)))


def deflated_sharpe(xs, trial_sharpes):
    """Observed cross-trial SD is mandatory, never inferred from winner alone.

    Effective independent trials are conservatively the supplied trial count.
    Trial Sharpes must use the same horizon, costs, and evaluation protocol.
    """
    ss=finite_sample(trial_sharpes)
    if not ss: return {"available":False,"reason":"Full trial Sharpe distribution required"}
    if len(ss)==1: hurdle=0.
    else:
        gamma=.5772156649015329
        hurdle=stdev(ss)*((1-gamma)*norm.ppf(1-1/len(ss))+gamma*norm.ppf(1-1/(len(ss)*math.e)))
    return {"available":True,"probability":probabilistic_sharpe(xs,float(hurdle)),"benchmark":float(hurdle),"trials":len(ss),"independence_assumption":True}


def expectancy_test(xs, confidence=.95):
    xs=finite_sample(xs); n=len(xs)
    if n<2: return {"available":False,"n":n}
    avg=mean(xs); sd=stdev(xs)
    if sd==0:
        return {"available":False,"n":n,"mean":avg,"reason":"Zero variance: significance undefined"}
    se=sd/math.sqrt(n); critical=float(t.ppf((1+confidence)/2,n-1))
    return {"available":True,"n":n,"mean":avg,"ci":[avg-critical*se,avg+critical*se],"pvalue_positive":float(t.sf(avg/se,n-1)),"assumption":"IID net trade observations"}


def welch_test(first, second):
    first,second=finite_sample(first),finite_sample(second)
    if min(len(first),len(second))<2 or (stdev(first)==0 and stdev(second)==0):
        return {"available":False}
    result=ttest_ind(first,second,equal_var=False)
    return {"available":True,"statistic":float(result.statistic),"pvalue_two_sided":float(result.pvalue),"assumption":"Independent groups"}


def summarize(xs):
    xs=finite_sample(xs)
    if not xs: return {"available":False,"n":0}
    wins=sum(x>0 for x in xs)
    return {"available":True,"n":len(xs),"net":sum(xs),"expectancy":mean(xs),"win_rate":wins/len(xs),"win_rate_ci95":list(wilson_interval(wins,len(xs))),"max_drawdown":max_drawdown(xs),"sharpe":sharpe(xs),"psr":probabilistic_sharpe(xs),"expectancy_test":expectancy_test(xs)}


def sequence_risk(xs, runs=10000, ruin_budget=10., seed=1729):
    """Permutation addresses ordering risk only; it cannot test expectancy.

    Additive PnL/risk-unit paths; ruin means cumulative PnL <= -budget.
    All permutations preserve mean exactly. No expectancy CI is fabricated.
    """
    xs=finite_sample(xs)
    if not xs: return {"available":False}
    if not 100<=runs<=100000 or ruin_budget<=0: raise ValueError("Invalid simulation configuration")
    rng=random.Random(seed); drawdowns=[]; ruined=0
    for _ in range(runs):
        path=xs[:]; rng.shuffle(path); eq=0.; hit=False
        for p in path:
            eq+=p
            hit=hit or eq<=-ruin_budget
        ruined+=hit
        drawdowns.append(max_drawdown(path))
    drawdowns.sort()
    return {"available":True,"method":"permutation_additive_pnl","runs":runs,"seed":seed,"ruin_budget":ruin_budget,"ruin_probability":ruined/runs,"max_drawdown_p50":drawdowns[int(.5*(runs-1))],"max_drawdown_p95":drawdowns[int(.95*(runs-1))],"expectancy_test":False,"limitation":"Ordering only; preserves sample expectancy and ignores unseen tails"}


def block_bootstrap_expectancy(xs, block_size=5, runs=2000, seed=1729):
    """Circular moving-block bootstrap allows local dependence, not stationarity guarantees."""
    xs=finite_sample(xs)
    if len(xs)<max(20,block_size*4): return {"available":False,"reason":"Insufficient blocks"}
    if block_size<1 or runs<100: raise ValueError("Invalid bootstrap configuration")
    rng=random.Random(seed); means=[]; n=len(xs)
    for _ in range(runs):
        sample=[]
        while len(sample)<n:
            start=rng.randrange(n)
            sample.extend(xs[(start+j)%n] for j in range(block_size))
        means.append(mean(sample[:n]))
    means.sort()
    return {"available":True,"mean_ci95":[means[int(.025*(runs-1))],means[int(.975*(runs-1))]],"block_size":block_size,"runs":runs,"seed":seed,"assumption":"Locally dependent stationary observations"}
