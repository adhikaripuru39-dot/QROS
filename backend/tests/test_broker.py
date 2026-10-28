from datetime import datetime,timedelta,timezone
from types import SimpleNamespace as N
from unittest.mock import Mock
import pytest
from qros.broker.base import OrderRequest,client_tag
from qros.broker.null_adapter import NullAdapter
from qros.broker.mt5_adapter import MT5Adapter

@pytest.fixture
def fake():
    module=Mock()
    module.initialize.return_value=True
    module.terminal_info.return_value=N(connected=True,trade_allowed=True)
    module.positions_get.return_value=[]
    module.orders_get.return_value=[]
    module.history_deals_get.return_value=[]
    module.symbol_info_tick.return_value=N(bid=1.1,ask=1.1001,time_msc=int(datetime.now(timezone.utc).timestamp()*1000),time=int(datetime.now(timezone.utc).timestamp()))
    module.symbol_info.return_value=N(filling_mode=1)
    module.ORDER_FILLING_FOK=0;module.ORDER_FILLING_IOC=1;module.ORDER_FILLING_RETURN=2
    module.TRADE_ACTION_DEAL=1;module.ORDER_TYPE_BUY=0;module.ORDER_TYPE_SELL=1;module.ORDER_TIME_GTC=0
    module.order_check.return_value=N(retcode=0,comment="ok")
    module.order_send.return_value=N(retcode=10009,order=17,price=1.1001,volume=.1,comment='done')
    return module

@pytest.fixture
def req():return OrderRequest('test-order','EURUSD','buy',.1,1.099)

def adapter(fake,**kwargs):
    broker=MT5Adapter(mt5_module=fake,verify_attempts=1,verify_sleep=0,allow_orders=True,**kwargs)
    assert broker.connect().connected
    broker.clock_verified=True;broker._utc_offset_seconds=0
    return broker

def test_null_broker_never_fabricates(req):
    broker=NullAdapter()
    assert not broker.connect().connected
    assert broker.positions() is None and broker.account_info() is None
    assert not broker.send_market_order(req).ok
    assert not broker.cancel_order('1').ok and not broker.close_position('1').ok

def test_reported_done_is_not_a_verified_fill(fake,req):
    result=adapter(fake).send_market_order(req)
    assert not result.ok and not result.verified

def test_duplicate_order_is_never_resent(fake,req):
    fake.positions_get.return_value=[N(comment=client_tag(req.client_order_id),ticket=17)]
    result=adapter(fake).send_market_order(req)
    assert result.duplicate and not result.ok
    fake.order_send.assert_not_called()

def test_verified_fill(fake,req):
    pos=N(comment=client_tag(req.client_order_id),ticket=17,price_open=1.1001,volume=.1,sl=1.099)
    fake.positions_get.side_effect=[[],[pos],[pos]]
    result=adapter(fake).send_market_order(req)
    assert result.ok and result.verified and result.filled_volume==.1

def test_stop_required(fake,req):
    req=OrderRequest('bad','EURUSD','buy',.1,0)
    assert not adapter(fake).send_market_order(req).ok
    fake.order_send.assert_not_called()

def test_quote_age_uses_tick_changes(fake):
    clock=Mock(return_value=datetime(2026,10,20,tzinfo=timezone.utc))
    broker=adapter(fake,clock=clock)
    first=broker.quote('EURUSD')
    clock.return_value+=timedelta(seconds=30)
    assert broker.quote('EURUSD').time==first.time
    fake.symbol_info_tick.return_value.time_msc=int(clock.return_value.timestamp()*1000)
    assert broker.quote('EURUSD').time==clock.return_value

def test_pending_order_is_not_a_verified_fill(fake,req):
    broker=adapter(fake)
    fake.orders_get.side_effect=[[],[N(comment=client_tag(req.client_order_id),ticket=17)]]
    result=broker.send_market_order(req)
    assert not result.ok and not result.verified

def test_unknown_position_query_is_not_closed(fake):
    fake.positions_get.return_value=None
    result=adapter(fake).close_position('17')
    assert not result.ok and not result.verified

def test_unknown_order_query_is_not_cancelled(fake):
    fake.orders_get.return_value=None
    result=adapter(fake).cancel_order('17')
    assert not result.ok and not result.verified

def test_missing_broker_stop_is_not_verified(fake,req):
    pos=N(comment=client_tag(req.client_order_id),ticket=17,price_open=1.1001,volume=.1,sl=0)
    fake.positions_get.side_effect=[[],[pos]]
    assert not adapter(fake).send_market_order(req).verified
