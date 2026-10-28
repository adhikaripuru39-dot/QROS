"""Broker demo experimentation cannot become validation/funded permission."""
from datetime import datetime,timedelta,timezone
from dataclasses import replace
import pytest
from qros.db.models import Strategy,SystemState
from qros.db.session import session_scope
from qros.services import settings_store as st
from qros.services.demo_testing import grant_errors
from qros.services.evidence import canonical_hash,strategy_eligibility
from qros.services.execution import account_key
from qros.research.runner import implementation_hash
from qros.broker.base import AccountInfo
from qros.config.settings import Settings
from qros.config.schemas import TradingMode
from qros.risk.gate import ALLOWED_STATUS_BY_MODE
from qros.governance.lifecycle import StrategyStatus,check_transition,TransitionError


@pytest.fixture
def permission(factory):
    now=datetime.now(timezone.utc)
    a=AccountInfo('demo-fixture','isolated',True,'USD',100000,100000,0,100000,100,True)
    with session_scope(factory) as db:
        st.seed_if_empty(db)
        limits=st.internal_limits(db).model_dump()
        limits.update(risk_per_trade_pct=.05,max_open_positions=1,max_trades_per_day=6,
            daily_warning_pct=.25,daily_stop_pct=.5,max_total_open_risk_pct=.1,
            max_risk_per_instrument_pct=.1,max_currency_risk_pct=.1,max_session_loss_pct=.5)
        st.set_internal_limits(db,limits,'fixture')
        strategy=Strategy(id='test',hypothesis_id='momentum',family='trend',name='test',status='DEMO_TESTING',spec={'runtime':{'symbol':'EURUSD'}})
        db.add(strategy)
        g={'actor_kind':'owner','programme':'2-Step Free Trial','funded':False,
            'server':a.server,'account_key':account_key(a,'demo'),'firm_id':st.active_firm(db).id,
            'authorized_at':now.isoformat(),'expires_at':(now+timedelta(days=7)).isoformat(),
            'strategy_hash':canonical_hash({'hypothesis':strategy.hypothesis_id,'runtime':strategy.spec['runtime']}),
            'code_hash':implementation_hash()}
        db.add(SystemState(key='demo_test_grant:test',data=g,updated_at=now))
    return factory,a,now


def test_exact_demo_scope_only(permission):
    factory,a,now=permission
    with session_scope(factory) as db:
        strategy=db.get(Strategy,'test')
        assert not grant_errors(db,strategy,'demo',now,a,Settings(_env_file=None,news_filter_enabled=True))
        for mode in ('live','paper','off'):
            assert strategy_eligibility(db,strategy,mode)
        assert 'DEMO_TEST_ACCOUNT_MISMATCH' in grant_errors(db,strategy,'demo',now,replace(a,login='changed'))
        assert 'DEMO_TEST_ACCOUNT_MISMATCH' in grant_errors(db,strategy,'demo',now,replace(a,is_demo=False))
        assert grant_errors(db,strategy,'demo',now,a,Settings(_env_file=None,news_filter_enabled=False))
        assert grant_errors(db,strategy,'demo',now,a,Settings(_env_file=None,news_filter_enabled=True,live_trading_enabled=True))
        assert grant_errors(db,strategy,'demo',now+timedelta(days=8),a)


@pytest.mark.parametrize('change',['runtime','code','limits','missing','malformed'])
def test_changes_invalidate_permission(permission,change):
    factory,a,now=permission
    with session_scope(factory) as db:
        strategy=db.get(Strategy,'test');row=db.get(SystemState,'demo_test_grant:test')
        if change=='runtime':strategy.spec={'runtime':{'symbol':'GBPUSD'}}
        if change=='code':row.data={**row.data,'code_hash':'0'*64}
        if change=='missing':db.delete(row);db.flush()
        if change=='malformed':row.data={}
        if change=='limits':
            limits=st.internal_limits(db).model_dump();limits['risk_per_trade_pct']=.1
            st.set_internal_limits(db,limits,'fixture')
        assert grant_errors(db,strategy,'demo',now,a)


def test_demo_test_never_promotes_to_live():
    assert 'DEMO_TESTING' in ALLOWED_STATUS_BY_MODE[TradingMode.DEMO]
    assert 'DEMO_TESTING' not in ALLOWED_STATUS_BY_MODE[TradingMode.LIVE]
    assert 'DEMO_TESTING' not in ALLOWED_STATUS_BY_MODE[TradingMode.PAPER]
    with pytest.raises(TransitionError):
        check_transition(StrategyStatus.IDEA,StrategyStatus.DEMO_TESTING,'system',{'demo_test_grant':'test'})
    with pytest.raises(TransitionError):
        check_transition(StrategyStatus.DEMO_TESTING,StrategyStatus.LIVE_APPROVED,'owner',{})


def test_deferred_arm_waits_for_readiness_and_is_consumed(permission,monkeypatch):
    from qros.db.models import ControlState
    from qros.services.executor import Executor
    from qros.broker.null_adapter import NullAdapter
    factory,a,now=permission
    ex=Executor(Settings(_env_file=None,news_filter_enabled=True,order_execution_enabled=True),NullAdapter(),factory,clock=lambda:now)
    ex.snapshot={'account':a};ex.connected=True
    def start(db,p,when):
        db.get(ControlState,1).run_state='running'
        return 'done',{'run_state':'running'}
    monkeypatch.setattr(ex,'_cmd_start',start)
    with session_scope(factory) as db:
        c=db.get(ControlState,1);c.trading_mode='demo';c.active_strategy_ids=['test']
        assert ex._cmd_arm_demo(db,{},now)[0]=='done'
        monkeypatch.setattr('qros.services.readiness.readiness',lambda *a,**k:{'ready_for_demo':False})
        ex._activate_pending_demo(db,now)
        assert c.run_state=='paused_entries' and db.get(SystemState,'demo_forward_arm').data['pending']
        monkeypatch.setattr('qros.services.readiness.readiness',lambda *a,**k:{'ready_for_demo':True})
        ex._activate_pending_demo(db,now)
        assert c.run_state=='running' and not db.get(SystemState,'demo_forward_arm').data['pending']


@pytest.mark.parametrize('action',['restart','stop','account_change','expiry','live_mode'])
def test_pending_arm_cancelled_on_recovery_or_owner_changes(permission,action):
    from qros.db.models import ControlState,ControlCommand
    from qros.services.executor import Executor
    from qros.broker.null_adapter import NullAdapter
    factory,a,now=permission
    ex=Executor(Settings(_env_file=None,news_filter_enabled=True,order_execution_enabled=True),NullAdapter(),factory,clock=lambda:now)
    ex.snapshot={'account':a};ex.connected=True
    with session_scope(factory) as db:
        c=db.get(ControlState,1);c.trading_mode='demo';c.active_strategy_ids=['test']
        assert ex._cmd_arm_demo(db,{},now)[0]=='done'
    if action=='restart':ex.startup()
    else:
        with session_scope(factory) as db:
            if action=='stop':
                db.add(ControlCommand(command='stop',payload={},actor='owner',status='pending',created_at=now));db.flush()
                ex._process_commands(db,now)
            elif action=='account_change':ex.snapshot={'account':replace(a,login='changed')}
            elif action=='live_mode':db.get(ControlState,1).trading_mode='live'
            ex._activate_pending_demo(db,now+timedelta(days=8) if action=='expiry' else now)
    with session_scope(factory) as db:
        assert not db.get(SystemState,'demo_forward_arm').data['pending']
        assert db.get(ControlState,1).run_state!='running'
