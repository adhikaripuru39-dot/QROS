"""Broker IDs repeat across account/mode boundaries; journal ownership must not."""
from dataclasses import replace
from datetime import datetime,timezone
from sqlalchemy import select
import pytest
from qros.broker.base import AccountInfo,BrokerPosition,OrderResult,client_tag
from qros.db.models import Trade,OrderLedger,ControlState,SystemState
from qros.db.session import session_scope
from qros.services.execution import account_key,bind_broker_ticket,raw_trade_ticket,TicketBindingError,execute_intent
from qros.services.reconciliation import reconcile
from test_execution_pipeline import pipeline

NOW=datetime(2026,10,20,10,tzinfo=timezone.utc)
ACCOUNT=AccountInfo('fixture','isolated',True,'USD',100000,100000,0,100000,100,True)


class Broker:
    def __init__(self,account,client,ticket='P1',external=False,volume=.1):
        self.account=account
        self.position_list=[BrokerPosition(ticket,'EURUSD','buy',volume,1.1,1.101,1.09,1.12,0,770001,client_tag(client),NOW)]
        if external:self.position_list.append(BrokerPosition('external','EURUSD','buy',.1,1.1,1.101,1.09,1.12,0,0,'manual',NOW))
    def account_info(self):return self.account
    def positions(self):return self.position_list
    def pending_orders(self):return []
    def historical_deals(self,since):return []


def seed(db,account,mode,client,status='unknown'):
    if db.get(ControlState,1) is None:db.add(ControlState(id=1,trading_mode=mode,run_state='running',kill_switch=False))
    db.add(OrderLedger(client_order_id=client,account_key=account_key(account,mode),strategy_id='s1',symbol='EURUSD',mode=mode,status=status,
        request={'entry_price':1.1,'stop_price':1.09,'take_profit':1.12,'volume':.1,'side':'buy'},result={},decision={},created_at=NOW,updated_at=NOW))
    db.flush()


def legacy_trade(client='legacy'):
    return Trade(mode='demo',strategy_id='s1',symbol='EURUSD',side='buy',volume=.1,entry_time=NOW,entry_price=1.1,
                 intended_entry=1.1,sl=1.09,tp=1.12,reason='legacy',broker_ticket='900',client_order_id=client)


def test_raw_ticket_reuse_across_accounts_and_modes_isolated_and_external_retained(factory):
    scenarios=[(ACCOUNT,'paper','paper-1'),(ACCOUNT,'demo','demo-1'),(replace(ACCOUNT,login='other'),'demo','demo-2')]
    with session_scope(factory) as db:
        for account,mode,client in scenarios:
            seed(db,account,mode,client)
            reconcile(db,Broker(account,client,external=True),NOW,mode);db.flush()
            assert db.get(OrderLedger,client).status=='verified'
            assert db.get(SystemState,'reconciliation').data['external_positions']==['external']
        trades=list(db.execute(select(Trade)).scalars())
        assert len(trades)==3 and len({t.broker_ticket for t in trades})==3
        assert all(len(t.broker_ticket)==32 for t in trades)
        for trade,(account,mode,_) in zip(trades,scenarios):
            assert raw_trade_ticket(db,trade,account_key(account,mode),mode)=='P1'


def test_known_raw_ticket_comparison_survives_scoping_and_repeated_reconciliation(factory):
    with session_scope(factory) as db:
        seed(db,ACCOUNT,'demo','c1')
        broker=Broker(ACCOUNT,'c1','900')
        reconcile(db,broker,NOW,'demo');db.flush()
        stored=db.execute(select(Trade)).scalar_one().broker_ticket
        reconcile(db,broker,NOW,'demo');db.flush()
        assert db.get(SystemState,'reconciliation').data['clean']
        assert db.execute(select(Trade)).scalar_one().broker_ticket==stored


def test_legacy_normalizes_only_with_explicit_durable_account_binding(factory):
    with session_scope(factory) as db:
        seed(db,ACCOUNT,'demo','legacy',status='verified')
        trade=legacy_trade();db.add(trade);db.flush()
        assert raw_trade_ticket(db,trade,account_key(ACCOUNT,'demo'),'demo')=='900'
        assert trade.broker_ticket.startswith('q:')
        with pytest.raises(TicketBindingError):raw_trade_ticket(db,trade,account_key(replace(ACCOUNT,login='other'),'demo'),'demo')


def test_ambiguous_preledger_trade_does_not_claim_external_position(factory):
    with session_scope(factory) as db:
        db.add(ControlState(id=1,trading_mode='demo',run_state='running',kill_switch=False))
        trade=legacy_trade();db.add(trade);db.flush()
        broker=Broker(ACCOUNT,'unrelated','900')
        reconcile(db,broker,NOW,'demo')
        report=db.get(SystemState,'reconciliation').data
        assert not report['clean'] and report['external_positions']==['900']
        assert any('AMBIGUOUS_LEGACY' in x for x in report['issues'])
        assert trade.broker_ticket=='900'
        assert db.get(ControlState,1).run_state=='paused_entries'
        assert raw_trade_ticket(db,trade,account_key(ACCOUNT,'demo'),'demo',explicit_binding={
            'account_key':account_key(ACCOUNT,'demo'),'mode':'demo','raw_ticket':'900',
            'client_order_id':'legacy','source':'owner-confirmed imported broker ledger'})=='900'


def test_same_account_position_reuse_is_not_a_second_journal_trade(factory):
    with session_scope(factory) as db:
        seed(db,ACCOUNT,'demo','first')
        reconcile(db,Broker(ACCOUNT,'first','900'),NOW,'demo');db.flush()
        seed(db,ACCOUNT,'demo','second')
        db.get(ControlState,1).run_state='running'
        reconcile(db,Broker(ACCOUNT,'second','900'),NOW,'demo');db.flush()
        assert len(list(db.execute(select(Trade)).scalars()))==1
        assert db.get(OrderLedger,'second').status=='unknown'
        assert any('TICKET_ALREADY_BOUND' in i for i in db.get(SystemState,'reconciliation').data['issues'])
        assert db.get(ControlState,1).run_state=='paused_entries'


def test_execution_scopes_real_fill_and_reused_ticket_pauses_without_rollback(pipeline):
    factory,broker,settings,intent=pipeline
    assert execute_intent(factory,broker,settings,intent,'first',NOW)['status']=='verified'
    assert execute_intent(factory,broker,settings,intent,'second',NOW)['status']=='unknown'
    with session_scope(factory) as db:
        trade=db.execute(select(Trade)).scalar_one()
        ledger=db.get(OrderLedger,'first')
        assert raw_trade_ticket(db,trade,ledger.account_key,'demo')=='900'
        assert db.get(ControlState,1).run_state=='paused_entries'


def test_paper_rejection_without_fill_is_not_submitted_but_exceptions_unknown(pipeline):
    factory,broker,settings,intent=pipeline
    with session_scope(factory) as db:
        db.get(ControlState,1).trading_mode='paper'
        db.get(SystemState,'reconciliation').data={'available':True,'clean':True,'account_key':account_key(broker.account_info(),'paper')}
    broker.result=OrderResult(False,message='simulated margin rejection')
    result=execute_intent(factory,broker,settings,intent,'paper-rejected',NOW)
    assert result['status']=='rejected' and result['result']['details']['outcome']=='not_submitted'
    def fail(_):raise RuntimeError('paper outcome after uncertain commit')
    broker.send_market_order=fail
    result=execute_intent(factory,broker,settings,intent,'paper-error',NOW)
    assert result['status']=='unknown'
