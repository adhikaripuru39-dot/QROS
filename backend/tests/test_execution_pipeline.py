"""Isolated broker fixtures; these tests never import/call MetaTrader5."""
from dataclasses import replace
from datetime import datetime,timezone
from sqlalchemy import select
import pytest
from qros.broker.base import AccountInfo,Quote,OrderResult,ConnectionStatus
from qros.config.settings import Settings
from qros.db.models import ControlState,OrderLedger,RiskStateRow,Strategy,Trade,SystemState
from qros.db.session import session_scope
from qros.risk.gate import OrderIntent
from qros.services.execution import execute_intent,account_key
from qros.services import settings_store as st

NOW=datetime(2026,10,20,10,tzinfo=timezone.utc)


@pytest.fixture
def pipeline(factory,spec,monkeypatch):
    # Evidence has its own integration suite. Isolate the execution boundary.
    monkeypatch.setattr('qros.services.evidence.strategy_eligibility',lambda *args:[])
    account=AccountInfo('fixture','isolated',True,'USD',100000,100000,0,100000,100,True)
    class Broker:
        sent=0
        observations=0
        change_account=False
        result=OrderResult(True,ticket='900',retcode=10009,fill_price=1.1001,filled_volume=.1,verified=True,details={'broker_sl':1.0991})
        def account_info(self):
            self.observations+=1
            return replace(account,login='switched') if self.change_account and self.observations>1 else account
        def positions(self):return []
        def quote(self,symbol):return Quote(symbol,1.1,1.1001,NOW)
        def contract_spec(self,symbol):return spec
        def realized_pnl_since(self,since):return 0.
        def ping(self):return ConnectionStatus(True)
        def margin_required(self,*args):return 100.
        def send_market_order(self,request):
            with session_scope(factory) as db:
                assert db.get(OrderLedger,request.client_order_id).status=='submitting'
            self.sent+=1
            return self.result
    broker=Broker()
    with session_scope(factory) as db:
        st.seed_if_empty(db)
        firm=st.active_firm(db)
        data=firm.model_dump(mode='json');data['is_example']=False;data['news']['enabled']=False
        st.upsert_firm_profile(db,data,'fixture')
        ctrl=db.get(ControlState,1);ctrl.trading_mode='demo';ctrl.run_state='running';ctrl.active_strategy_ids=['s1']
        db.add(Strategy(id='s1',hypothesis_id='momentum',family='momentum',name='isolated',status='DEMO_APPROVED',spec={}))
        db.add(RiskStateRow(id=1,computed_at=NOW,firm_id=firm.id,trading_day='2026-10-20',data={'anchor_method':'observed_at_reset','sod_balance':100000,'sod_equity':100000},hwm_equity=100000,hwm_eod_balance=100000))
        db.add(SystemState(key='reconciliation',updated_at=NOW,data={'available':True,'clean':True,'account_key':account_key(account,'demo')}))
    return factory,broker,Settings(_env_file=None,order_execution_enabled=True),OrderIntent('EURUSD','buy',1.1001,1.0991,.1,'s1','DEMO_APPROVED')


def test_durable_intent_precedes_send_and_duplicate_never_resends(pipeline):
    factory,broker,settings,intent=pipeline
    assert execute_intent(factory,broker,settings,intent,'unique',NOW)['status']=='verified'
    assert execute_intent(factory,broker,settings,intent,'unique',NOW)['status']=='duplicate'
    assert broker.sent==1
    with session_scope(factory) as db:
        assert len(list(db.execute(select(Trade)).scalars()))==1


@pytest.mark.parametrize('result',[OrderResult(False,retcode=10012,message='timeout'),OrderResult(False,retcode=10031,message='connection'),OrderResult(False,retcode=10008,message='pending'),OrderResult(True,ticket='900',retcode=10009,fill_price=1.1001,filled_volume=.1,verified=True)])
def test_unknown_timeout_pending_or_unproven_stop_pauses_and_never_resends(pipeline,result):
    factory,broker,settings,intent=pipeline;broker.result=result
    assert execute_intent(factory,broker,settings,intent,'uncertain',NOW)['status']=='unknown'
    assert execute_intent(factory,broker,settings,intent,'uncertain',NOW)['status']=='duplicate'
    assert execute_intent(factory,broker,settings,intent,'new-id',NOW)['status']=='rejected'
    assert broker.sent==1
    with session_scope(factory) as db:
        assert db.get(ControlState,1).run_state=='paused_entries'
        assert not list(db.execute(select(Trade)).scalars())


def test_partial_fill_journals_actual_volume_and_pauses(pipeline):
    factory,broker,settings,intent=pipeline
    broker.result=OrderResult(True,ticket='900',retcode=10010,fill_price=1.1001,filled_volume=.04,verified=True,details={'broker_sl':1.0991})
    result=execute_intent(factory,broker,settings,intent,'partial',NOW)
    assert result['status']=='verified' and result['result']['partial_fill']
    with session_scope(factory) as db:
        assert db.execute(select(Trade)).scalar_one().volume==.04
        assert db.get(ControlState,1).run_state=='paused_entries'


def test_terminal_account_switch_after_gate_prevents_send(pipeline):
    factory,broker,settings,intent=pipeline;broker.change_account=True
    assert execute_intent(factory,broker,settings,intent,'switch',NOW)['status']=='rejected'
    assert broker.sent==0


def test_unclean_reconciliation_blocks_send(pipeline):
    factory,broker,settings,intent=pipeline
    with session_scope(factory) as db:db.get(SystemState,'reconciliation').data={'available':False,'clean':False}
    result=execute_intent(factory,broker,settings,intent,'unsafe',NOW)
    assert result['status']=='rejected' and 'RECONCILIATION_MISSING_STALE_OR_UNCLEAN' in result['reasons']
    assert broker.sent==0


@pytest.mark.parametrize('scope',['correct','changed_account','expired','news_disabled','live_host_enabled'])
def test_demo_experiment_permission_enforced_at_send_boundary(pipeline,scope):
    from datetime import timedelta
    from qros.services.evidence import canonical_hash
    from qros.research.runner import implementation_hash
    factory,broker,settings,intent=pipeline
    settings.news_filter_enabled=True
    # Calendar checks have separate boundary tests; isolate grant scope here.
    import qros.services.execution as execution
    original=execution.configured_news
    execution.configured_news=lambda *a,**kw:(True,False,'OK')
    try:
        with session_scope(factory) as db:
            strategy=db.get(Strategy,'s1');strategy.status='DEMO_TESTING'
            limits=st.internal_limits(db).model_dump()
            limits.update(risk_per_trade_pct=.05,max_open_positions=1,max_trades_per_day=6,
                daily_warning_pct=.25,daily_stop_pct=.5,max_total_open_risk_pct=.1,
                max_risk_per_instrument_pct=.1,max_currency_risk_pct=.1,max_session_loss_pct=.5)
            st.set_internal_limits(db,limits,'fixture')
            grant={'actor_kind':'owner','programme':'2-Step Free Trial','funded':False,
                'server':broker.account_info().server,'account_key':account_key(broker.account_info(),'demo'),
                'firm_id':st.active_firm(db).id,'authorized_at':(NOW-timedelta(hours=1)).isoformat(),
                'expires_at':(NOW+timedelta(days=7)).isoformat(),
                'strategy_hash':canonical_hash({'hypothesis':strategy.hypothesis_id,'runtime':{}}),
                'code_hash':implementation_hash()}
            if scope=='changed_account':grant['account_key']='wrong'
            if scope=='expired':grant['expires_at']=(NOW-timedelta(minutes=1)).isoformat()
            db.add(SystemState(key='demo_test_grant:s1',data=grant,updated_at=NOW))
        if scope=='news_disabled':settings.news_filter_enabled=False
        if scope=='live_host_enabled':settings.live_trading_enabled=True
        result=execute_intent(factory,broker,settings,replace(intent,strategy_status='DEMO_TESTING'),'demo-scope',NOW)
        assert result['status']==('verified' if scope=='correct' else 'rejected')
        assert broker.sent==(1 if scope=='correct' else 0)
    finally:execution.configured_news=original


@pytest.mark.parametrize('source',['missing','blackout','clear'])
def test_internal_native_news_rechecks_at_order_boundary(pipeline,tmp_path,source):
    import json
    factory,broker,settings,intent=pipeline
    path=tmp_path/'calendar.json';utc=int(NOW.timestamp());server=utc+10800
    raw={'schema':2,'source':'mt5_builtin_calendar','read_only':True,'complete':True,'errors':0,
         'generated_utc':utc,'finished_utc':utc+1,'server_time':server,'server':'isolated',
         'query_from_server':server-86400,'query_until_server':server+86400,
         'currencies':['USD','EUR'],'events':[]}
    if source=='blackout':raw['events']=[{'time_server':server,'importance':3,'currency':'USD','exact_time':True}]
    if source!='missing':path.write_text(json.dumps(raw))
    settings=settings.model_copy(update={'news_filter_enabled':True,'news_calendar_path':path})
    result=execute_intent(factory,broker,settings,intent,'news-'+source,NOW)
    if source=='clear':assert result['status']=='verified' and broker.sent==1
    else:
        assert result['status']=='rejected' and broker.sent==0
        assert any('NEWS' in reason for reason in result['reasons'])
