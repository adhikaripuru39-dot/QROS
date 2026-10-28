from dataclasses import replace
from qros.backtest import Bar, BacktestConfig
from qros.research.regimes import characterize
from qros.research.registry import signals, strategy_registry
from qros.research.runner import run_research
import pytest


def bars(n=400):
    # Isolated deterministic fixture, never dashboard/report production data.
    data=[]
    for i in range(n):
        op=1+i*.00001
        close=op+(.00005 if i%7<4 else -.00004)
        data.append(Bar(1700000000+i*900,op,max(op,close)+.00002,min(op,close)-.00002,close,.00002))
    return data


def test_all_registered_hypotheses_are_falsifiable_research_only():
    specs=strategy_registry()
    assert len(specs)==len({x.id for x in specs})==11
    assert all(x.rationale and x.entry and x.exit and x.protective_stop and x.failure_conditions and x.status=="RESEARCH_ONLY" for x in specs)


@pytest.mark.parametrize("sid",[x.id for x in strategy_registry()])
def test_every_signal_is_prefix_invariant(sid):
    source=bars(120)
    original=signals(source,sid)
    modified=source[:100]+[replace(x,open=x.open*2,high=x.high*2,low=x.low*2,close=x.close*2) for x in source[100:]]
    assert signals(modified,sid)[:100]==original[:100]
    assert signals(source[:100],sid)==original[:100]


def test_regime_features_are_finite_and_honest():
    assert characterize(bars(20))["available"] is False
    f=characterize(bars())
    assert f["available"] and f["atr"]>0 and 0<=f["atr_percentile"]<=1
    assert f["regime"] in {"trend","range"}
    with pytest.raises(ValueError): characterize(bars(),window=2)


def test_runner_preserves_holdout_and_binds_report(tmp_path):
    result=run_research(bars(),"fixture-version-sha256",tmp_path,config=BacktestConfig(),candidate_ids=["momentum"],finalize_oos=True,mc_runs=100)
    assert not result["eligible"] and not result["live_approved"]
    assert result["oos"]["evaluated"] is False
    assert result["binding"]["code_hash"] and result["binding"]["config_hash"]
    assert "execution_costs_verified" in result["preflight_failures"]
    assert not (tmp_path/"holdout_escrow.sqlite").exists()
    assert len(list(tmp_path.glob("research_*.json")))==1


def test_missing_multitimeframe_and_volume_never_fabricated():
    source=bars()
    assert not any(signals(source,"multi_timeframe"))
    assert not any(signals(source,"liquidity_proxy"))


def test_exit_tuning_changes_simulation_and_binds_runtime(tmp_path):
    data=[Bar(1700000000+i*3600,100+i*.1,100+i*.1+.05,100+i*.1-.05,100+i*.1+.04,0) for i in range(600)]
    def run(target):
        return run_research(data,'isolated-trending-fixture',tmp_path,config=BacktestConfig(),
            provenance={'timeframe_seconds':3600,'runtime_spec':{'atr_period':14,'stop_atr_multiple':2.,'target_atr_multiple':target}},
            candidate_ids=['momentum'])
    baseline=run(3.);proposed=run(6.)
    assert baseline['runtime_spec_hash']!=proposed['runtime_spec_hash']
    assert baseline['candidates'][0]['validation']['n']>0
    assert baseline['candidates'][0]['validation']['n']!=proposed['candidates'][0]['validation']['n']
    assert baseline['oos']['evaluated'] is False and proposed['oos']['evaluated'] is False
