import math
import pytest
from qros.validation.statistics import probabilistic_sharpe, deflated_sharpe, expectancy_test, sequence_risk, block_bootstrap_expectancy, welch_test
from qros.validation.protocol import EscrowLedger, HoldoutConsumed, chronological_split, walk_forward_optimize
from qros.validation.selection import pareto_front, profile_accepts, stress_gate


def test_psr_known_normal_moment_formula_and_deflation():
    sample=[-.01,.02,.01,-.005,.025]*40
    assert .5<probabilistic_sharpe(sample)<1.00000001
    assert probabilistic_sharpe(sample,1)<probabilistic_sharpe(sample,0)
    one=deflated_sharpe(sample,[.1])
    many=deflated_sharpe(sample,[i*.1 for i in range(20)])
    assert many["probability"]<one["probability"]
    assert probabilistic_sharpe([0]*100) is None
    assert deflated_sharpe(sample,[])["available"] is False
    with pytest.raises(ValueError): probabilistic_sharpe([0,math.nan])


def test_expectancy_and_welch_insufficient_or_degenerate():
    assert expectancy_test([1])["available"] is False
    assert expectancy_test([1]*100)["available"] is False
    result=expectancy_test([-1,2,3]*40)
    assert result["ci"][0]>0 and result["pvalue_positive"]<.05
    assert welch_test([1],[2])["available"] is False


def test_permutation_is_ordering_not_expectancy_test():
    sample=[-2,3,-2,3,-2,3]*10
    result=sequence_risk(sample,runs=100,ruin_budget=4)
    assert result==sequence_risk(sample,runs=100,ruin_budget=4)
    assert result["max_drawdown_p95"]>=result["max_drawdown_p50"]
    assert result["expectancy_test"] is False
    assert 0<=result["ruin_probability"]<=1
    assert block_bootstrap_expectancy(sample,runs=100)["available"]


def test_single_use_escrow_survives_reopen_and_parameter_change(tmp_path):
    path=tmp_path/"escrow.db"
    EscrowLedger(path).consume("actual_holdout_hash",{"candidate":"A","config":"1"})
    with pytest.raises(HoldoutConsumed):
        EscrowLedger(path).consume("actual_holdout_hash",{"candidate":"B","config":"2"})
    EscrowLedger(path).seal("actual_holdout_hash","report123")
    with pytest.raises(HoldoutConsumed): EscrowLedger(path).seal("actual_holdout_hash","overwrite")


def test_chronological_split_and_fold_selection():
    assert chronological_split(1000)=={"development":(0,600),"validation":(600,800),"oos":(800,1000)}
    seen=[]
    def score(candidate,partition):
        seen.append(tuple(partition)); return sum(partition)*candidate
    folds=walk_forward_optimize(list(range(100)),[1,2],score,train=30,test=10,embargo=2)
    assert len(folds)>1 and all(f["candidate"]==2 for f in folds)
    assert all(f["train"][1]+2==f["test"][0] for f in folds)
    assert max(seen[0])<min(seen[2])


def test_pareto_profiles_and_stress_gates():
    a={"expectancy":1,"win_rate":.7,"frequency":10,"max_drawdown":2}
    b={"expectancy":.5,"win_rate":.6,"frequency":9,"max_drawdown":3}
    assert pareto_front([a,b])==[a]
    assert profile_accepts({**a,"available":True,"n":100},"A")
    assert not profile_accepts({**a,"available":True,"n":99},"A")
    assert not stress_gate([1],[-1],{"trend":[1]*20,"range":[1]*20})["passed"]
    assert not stress_gate([1],[1],{"trend":[1]*20})["passed"]
    assert stress_gate([1],[1],{"trend":[1]*20,"range":[1]*20})["passed"]
