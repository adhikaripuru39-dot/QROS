import pytest
from qros.governance.lifecycle import StrategyStatus as S,TransitionError,check_transition,TRANSITIONS

@pytest.mark.parametrize('source,target',[(S.PAPER_TRADING,S.DEMO_APPROVED),(S.DEMO_APPROVED,S.LIVE_APPROVED),(S.LIVE_APPROVED,S.ACTIVE)])
def test_only_owner_can_approve(source,target):
    rule=next(r for r in TRANSITIONS[source] if r.target==target)
    evidence={k:'verified-reference' for k in rule.required_evidence}
    with pytest.raises(TransitionError,match='owner'):check_transition(source,target,'system',evidence)
    assert check_transition(source,target,'owner',evidence)==rule

def test_invalid_skip():
    with pytest.raises(TransitionError,match='not permitted'):check_transition(S.IDEA,S.ACTIVE,'owner',{})

def test_evidence_required():
    with pytest.raises(TransitionError,match='dataset_version'):check_transition(S.RESEARCH,S.BACKTESTED,'owner',{'experiment_id':'e1'})
