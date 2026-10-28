"""Executable research protocol on real supplied historical bid OHLC.

Historical cost models remain explicit assumptions. No report grants permission
to trade. Untouched OOS is not run unless explicitly requested and all preflight
gates pass; a failed attempt is still recorded as consumed.
"""
from __future__ import annotations
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
import hashlib
import json
from qros.backtest import BacktestEngine, BacktestConfig, Signal
from qros.validation.protocol import chronological_split, digest, EscrowLedger, walk_forward_windows
from qros.validation.statistics import summarize, sharpe, deflated_sharpe, sequence_risk, block_bootstrap_expectancy, welch_test
from qros.validation.selection import profile_accepts, pareto_front, stress_gate
from .registry import signals, registry_dicts
from .regimes import characterize, value


def implementation_hash():
    root=Path(__file__).resolve().parents[1]
    h=hashlib.sha256()
    for path in sorted(root.glob("**/*.py")):
        h.update(str(path.relative_to(root)).replace("\\","/").encode()); h.update(path.read_bytes())
    requirements=root.parent/"requirements.txt"
    if requirements.exists(): h.update(requirements.read_bytes())
    return h.hexdigest()


def _serial_bar(bar):
    return {k:value(bar,k) for k in ("time","open","high","low","close","spread")}


def run_research(bars,dataset_hash,output_dir,config=None,provenance=None,finalize_oos=False,candidate_ids=None,profile="B",embargo=1,mc_runs=10000):
    cfg=config or BacktestConfig(); provenance=dict(provenance or {})
    timeframe=provenance.get("timeframe_seconds")
    timeframe_valid=isinstance(timeframe,int) and not isinstance(timeframe,bool) and timeframe>0
    bars=tuple(bars); partitions=chronological_split(len(bars),embargo)
    if len(bars)>100000: raise ValueError("Batch capped at 100000 bars; partition first")
    if not dataset_hash: raise ValueError("Versioned source dataset hash required")
    if profile not in {"A","B","C"}: raise ValueError("Unknown selection profile")
    for index,b in enumerate(bars):
        import math
        fields=_serial_bar(b)
        if any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in fields.values()):
            raise ValueError("Finite numeric OHLC/spread/timestamps required")
        if index and b.time<=bars[index-1].time: raise ValueError("Strict chronological bars required")
        if min(b.open,b.high,b.low,b.close)<=0 or b.spread<0 or b.high<max(b.open,b.close,b.low) or b.low>min(b.open,b.close,b.high):
            raise ValueError("Invalid OHLC or spread")
    known={x["id"] for x in registry_dicts()}
    ids=list(candidate_ids or sorted(known))
    if not ids or len(set(ids))!=len(ids) or set(ids)-known: raise ValueError("Invalid candidate cohort")
    output=Path(output_dir); output.mkdir(parents=True,exist_ok=True)
    binding={"source_dataset_hash":dataset_hash,"bars_hash":digest([_serial_bar(b) for b in bars]),"code_hash":implementation_hash(),"config_hash":digest(asdict(cfg)),"protocol_hash":digest({"profile":profile,"embargo":embargo,"registry":registry_dicts(),"candidates":ids}),"provenance_hash":digest(provenance)}
    report={"schema":1,"created_at":datetime.now(timezone.utc).isoformat(),"binding":binding,"config":asdict(cfg),"provenance":provenance,"partitions":partitions,"registry":registry_dicts(),"selection_profile":profile,"candidates":[],"oos":{"evaluated":False},"eligible":False,"live_approved":False,
            "limitations":["Research only; all candidates unvalidated until complete protocol passes", "No fitted parameter optimization: walk-forward verifies fixed hypotheses", "Local escrow ledger cannot stop an administrator manually inspecting/copying raw data", "OHLC simulation uses adverse intrabar ordering; observed ask ticks and exact broker financing absent", "PSR/DSR assumes independent observations; block bootstrap only partially handles dependence"]}

    import math
    runtime = provenance.get('runtime_spec') or {}
    atr_period = runtime.get('atr_period',14)
    stop_multiple = runtime.get('stop_atr_multiple',2.)
    target_multiple = runtime.get('target_atr_multiple',3.)
    if (not isinstance(atr_period,int) or isinstance(atr_period,bool) or not 5<=atr_period<=50
            or any(not isinstance(x,(int,float)) or not math.isfinite(x) or not .5<=x<=10 for x in (stop_multiple,target_multiple))):
        raise ValueError('Invalid ATR/exit configuration')

    # Deliberately operate only on development/validation bars before escrow.
    cache={}
    def evaluate(sid,start,end,multiplier=1.):
        key=(sid,start,end,multiplier)
        if key in cache: return cache[key]
        warm=max(0,start-65); raw=bars[warm:end]
        data=tuple(replace(b,spread=b.spread*multiplier) for b in raw)
        completed=[{**_serial_bar(b),"time":b.time+timeframe,"open_time":b.time} for b in raw] if timeframe_valid else raw
        decisions=signals(completed,sid) if timeframe_valid or sid not in {"session_open","time_drift","multi_timeframe"} else [0]*len(raw)
        atr={}
        for index,decision in enumerate(decisions):
            if decision and warm+index>=start:
                tr=[max(x.high-x.low,abs(x.high-raw[j-1].close),abs(x.low-raw[j-1].close)) for j in range(max(1,index-atr_period+1),index+1) for x in [raw[j]]]
                atr[index]=mean(tr) if tr else 0.
        def strategy(history):
            i=len(history)-1
            if warm+i<start or not decisions[i] or atr.get(i,0)<=0: return None
            return Signal(decisions[i],cfg.min_lot,stop_multiple*atr[i],target_multiple*atr[i])
        result=BacktestEngine().run(data,strategy,replace(cfg,slippage=cfg.slippage*multiplier))
        pnls=[x.net_pnl for x in result.trades]
        metrics=summarize(pnls)
        metrics["frequency"]=len(pnls)/max(1,end-start)
        metrics["max_equity_drawdown_fraction"]=result.max_drawdown
        metrics["rejected_orders"]=len(result.rejected)
        regimes={}
        index_by_time={b.time:i for i,b in enumerate(raw)}
        for trade in result.trades:
            i=index_by_time[trade.entry_time]-1
            f=characterize(raw[max(0,i-64):i+1],include_distribution=False)
            label=f.get("regime","unavailable")
            regimes.setdefault(label,[]).append(trade.net_pnl)
        answer={"metrics":metrics,"pnls":pnls,"regimes":regimes,"assumptions":result.assumptions,"trades":[asdict(t) for t in result.trades]}
        cache[key]=answer
        return answer

    validation_end=partitions["validation"][1]
    trial_sharpes=[]; preflight={}
    for sid in ids:
        dev=evaluate(sid,*partitions["development"])
        val=evaluate(sid,*partitions["validation"])
        stressed=evaluate(sid,*partitions["validation"],2.)
        gate=stress_gate(val["pnls"],stressed["pnls"],val["regimes"])
        folds=[]
        train=max(100,int(validation_end*.5)); test=max(80,int(validation_end*.125))
        for a,b,c,d in walk_forward_windows(validation_end,train,test,True,embargo):
            fold=evaluate(sid,c,d)
            folds.append({"training_indices":[a,b],"test_indices":[c,d],"metrics":fold["metrics"],"parameters":"fixed preregistered parameters; no fold tuning"})
        row={"strategy_id":sid,"development":dev["metrics"],"validation":val["metrics"],"doubled_cost":stressed["metrics"],"stress":gate,"walk_forward":folds,"development_validation_welch":welch_test(dev["pnls"],val["pnls"])}
        report["candidates"].append(row)
        sr=sharpe(val["pnls"])
        if sr is not None: trial_sharpes.append(sr)
        preflight[sid]=(gate["passed"] and profile_accepts(val["metrics"],profile) and len(folds)>=2 and all(f["metrics"].get("n",0)>=10 and f["metrics"].get("expectancy",-1)>0 for f in folds))
    report["trial_count"]=len(ids)
    # Missing/degenerate trial Sharpes prohibit deflation, rather than silently
    # understating the search size by dropping unsuccessful experiments.
    complete_trials=len(trial_sharpes)==len(ids)
    frontier=pareto_front([{"strategy_id":r["strategy_id"],**r["validation"]} for r in report["candidates"] if r["validation"].get("available")])
    report["pareto_front"]=[r["strategy_id"] for r in frontier]
    ranked=sorted((r for r in report["candidates"] if preflight[r["strategy_id"]]),key=lambda r:(-r["validation"]["expectancy"],r["strategy_id"]))
    report["selected_candidate"]=ranked[0]["strategy_id"] if ranked else None
    report["preflight_failures"]=[]
    required=("coverage_verified","broker_specs_verified","execution_costs_verified","independent_trade_assumption_reviewed","runtime_equivalence_verified")
    if profile=="C": required+=("portfolio_independence_verified","daily_risk_cap_verified")
    report["preflight_failures"].extend(k for k in required if provenance.get(k) is not True)
    if not timeframe_valid: report["preflight_failures"].append("timeframe_seconds_unverified")
    runtime_spec=provenance.get("runtime_spec")
    if isinstance(runtime_spec,dict) and runtime_spec:
        report["runtime_spec_hash"]=digest(runtime_spec)
    else:
        report["preflight_failures"].append("runtime_spec_not_bound")
    if not ranked: report["preflight_failures"].append("no_candidate_passed_validation_stress_sample_and_walk_forward")
    if not complete_trials: report["preflight_failures"].append("incomplete_trial_sharpe_distribution")
    if finalize_oos and not report["preflight_failures"]:
        sid=report["selected_candidate"]; a,b=partitions["oos"]
        holdout_hash=digest([_serial_bar(x) for x in bars[a:b]])
        ledger=EscrowLedger(output/"holdout_escrow.sqlite")
        ledger.consume(holdout_hash,{**binding,"selected_candidate":sid,"development_validation_report_hash":digest(report)})
        oos=evaluate(sid,a,b); stressed=evaluate(sid,a,b,2.)
        dsr=deflated_sharpe(oos["pnls"],trial_sharpes)
        bootstrap=block_bootstrap_expectancy(oos["pnls"])
        stress=stress_gate(oos["pnls"],stressed["pnls"],oos["regimes"])
        metrics=oos["metrics"]
        checks={"profile":profile_accepts(metrics,profile),"psr":(metrics.get("psr") or 0)>=.95,"dsr":(dsr.get("probability") or 0)>=.95,"expectancy_significance":metrics.get("expectancy_test",{}).get("pvalue_positive",1)<.05,"bootstrap_positive":bootstrap.get("available",False) and bootstrap["mean_ci95"][0]>0,"stress":stress["passed"]}
        report["oos"]={"evaluated":True,"holdout_hash":holdout_hash,"metrics":metrics,"trades":oos["trades"],"dsr":dsr,"bootstrap":bootstrap,"stress":stress,"sequence_risk":sequence_risk(oos["pnls"],runs=mc_runs,ruin_budget=cfg.initial_cash*.05) if oos["pnls"] else {"available":False},"checks":checks}
        report["eligible"]=all(checks.values())
        ledger.seal(holdout_hash,digest(report))
    elif finalize_oos:
        report["oos"]["reason"]="Holdout preserved: preflight failed"
    stamp=report["created_at"].replace(":","").replace("+", "_")
    report["report_hash"]=digest(report)
    destination=output/f"research_{stamp}_{binding['bars_hash'][:10]}.json"
    with destination.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
    report["report_path"]=str(destination.resolve())
    return report
