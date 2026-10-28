from datetime import datetime,timezone
from sqlalchemy import select,func
from qros.broker.base import AccountInfo,BrokerPosition,BrokerOrder,client_tag
from qros.db.models import OrderLedger,ControlState,Trade,SystemState,BrokerDeal
from qros.db.session import session_scope
from qros.services.execution import account_key
from qros.services.reconciliation import reconcile

NOW=datetime(2026,10,20,10,tzinfo=timezone.utc)
ACCOUNT=AccountInfo('isolated','fixture',True,'USD',100000,100000,0,100000,100,True)


class Broker:
    position_list=[]
    order_list=[]
    deal_list=[]
    def account_info(self):return ACCOUNT
    def positions(self):return self.position_list
    def pending_orders(self):return self.order_list
    def historical_deals(self,since):return self.deal_list


def seed(db,status='unknown'):
    db.add(ControlState(id=1,trading_mode='demo',run_state='running',kill_switch=False))
    db.add(OrderLedger(client_order_id='c1',account_key=account_key(ACCOUNT,'demo'),strategy_id='s1',symbol='EURUSD',mode='demo',status=status,request={'entry_price':1.1,'stop_price':1.09,'take_profit':1.12,'volume':.1,'side':'buy'},result={},decision={},created_at=NOW,updated_at=NOW))
    db.flush()


def round_trip():
    return [
        {'ticket':'1','position_id':'900','comment':client_tag('c1'),'symbol':'EURUSD','type':0,'entry':0,'volume':.1,'price':1.1,'time':int(NOW.timestamp()),'profit':0.,'commission':-.35},
        {'ticket':'2','position_id':'900','comment':'normalized paper swap','symbol':'EURUSD','type':0,'entry':0,'volume':0.,'price':0.,'time':int(NOW.timestamp())+1,'profit':0.,'swap':-2.},
        {'ticket':'3','position_id':'900','comment':'[sl]','symbol':'EURUSD','type':1,'entry':1,'volume':.1,'price':1.101,'time':int(NOW.timestamp())+2,'profit':10.,'commission':-.35},
    ]


def test_closed_unknown_round_trip_uses_position_id_and_zero_volume_swap(factory):
    broker=Broker();broker.deal_list=round_trip()
    with session_scope(factory) as db:
        seed(db)
        reconcile(db,broker,NOW,'demo');db.flush()
        trade=db.execute(select(Trade)).scalar_one()
        assert trade.volume==.1 and trade.exit_price==1.101
        assert abs(trade.pnl-7.3)<1e-8 and trade.swap==-2.
        assert db.get(OrderLedger,'c1').status=='closed'
        reconcile(db,broker,NOW,'demo');db.flush()
        assert db.execute(select(func.count(Trade.id))).scalar()==1
        assert db.execute(select(func.count(BrokerDeal.key))).scalar()==3


def test_pending_receipt_does_not_become_a_fill(factory):
    broker=Broker();broker.order_list=[BrokerOrder('pending','EURUSD','buy',.1,1.1,1.09,1.12,client_tag('c1'))]
    with session_scope(factory) as db:
        seed(db);reconcile(db,broker,NOW,'demo')
        assert db.get(OrderLedger,'c1').status=='unknown'
        assert db.get(ControlState,1).run_state=='paused_entries'
        assert 'PENDING_ORDERS_REQUIRE_REVIEW' in db.get(SystemState,'reconciliation').data['issues']
        assert not list(db.execute(select(Trade)).scalars())


def test_partial_recovered_position_pauses_with_actual_journal_volume(factory):
    broker=Broker();broker.position_list=[BrokerPosition('900','EURUSD','buy',.04,1.1,1.101,1.09,1.12,0,770001,client_tag('c1'),NOW)]
    with session_scope(factory) as db:
        seed(db);reconcile(db,broker,NOW,'demo');db.flush()
        assert db.execute(select(Trade)).scalar_one().volume==.04
        assert db.get(ControlState,1).run_state=='paused_entries'
        assert 'PARTIAL_OR_MANUAL_VOLUME_CHANGE:900' in db.get(SystemState,'reconciliation').data['issues']


def test_unprotected_position_cannot_resolve_unknown(factory):
    broker=Broker();broker.position_list=[BrokerPosition('900','EURUSD','buy',.1,1.1,1.101,0.,1.12,0,770001,client_tag('c1'),NOW)]
    with session_scope(factory) as db:
        seed(db);reconcile(db,broker,NOW,'demo')
        assert db.get(OrderLedger,'c1').status=='unknown'
        assert 'UNPROTECTED_MANAGED_POSITION:900' in db.get(SystemState,'reconciliation').data['issues']


def test_mode_partition_prevents_cross_account_journal_recovery(factory):
    broker=Broker();broker.deal_list=round_trip()
    with session_scope(factory) as db:
        seed(db);reconcile(db,broker,NOW,'paper')
        assert db.get(OrderLedger,'c1').status=='unknown'
        assert not list(db.execute(select(Trade)).scalars())


def test_query_failure_pauses_entries(factory):
    broker=Broker();broker.position_list=None
    with session_scope(factory) as db:
        seed(db);reconcile(db,broker,NOW,'demo')
        assert db.get(ControlState,1).run_state=='paused_entries'
        assert db.get(SystemState,'reconciliation').data['available'] is False
