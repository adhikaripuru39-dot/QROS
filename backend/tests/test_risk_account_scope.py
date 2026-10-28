from types import SimpleNamespace as N
from qros.services.risk_identity import risk_day_scope

def test_risk_days_follow_real_account_across_off_demo_and_separate_paper():
    account=N(server='FTMO-Demo',login='123')
    assert risk_day_scope('firm',account,'off')==risk_day_scope('firm',account,'demo')
    assert risk_day_scope('firm',account,'paper')!=risk_day_scope('firm',account,'demo')
    assert risk_day_scope('firm',N(server='FTMO-Demo',login='456'),'demo')!=risk_day_scope('firm',account,'demo')
    assert len(risk_day_scope('verylongfirm'*20,account,'demo'))==64
