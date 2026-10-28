from dataclasses import replace
from datetime import datetime,timedelta,timezone
import pytest
from qros.config.schemas import RunState,TradingMode
from qros.risk.gate import GateContext,InstrumentState,OrderIntent,OpenPosition,check_order

@pytest.fixture
def setup(firm,limits,account,spec):
    now=datetime(2026,10,20,10,tzinfo=timezone.utc)
    inst=InstrumentState(spec,'EUR','USD',True,30,1.1,1.1001,now)
    ctx=GateContext(firm,limits,account,inst,[],now,TradingMode.PAPER,RunState.RUNNING,False,True,False,0,0,True,False,1000,30)
    return OrderIntent('EURUSD','buy',1.1001,1.0991,.1,'s1','PAPER_TRADING'),ctx

def test_valid(setup):
    order,ctx=setup
    assert check_order(order,ctx).approved

@pytest.mark.parametrize('change,reason',[({'kill_switch':True},'KILL_SWITCH_ACTIVE'),({'in_trading_hours':False},'OUTSIDE_TRADING_HOURS'),({'minutes_to_weekend_close':20},'TOO_CLOSE_TO_WEEKEND_CLOSE'),({'trades_today':12},'MAX_TRADES_PER_DAY')])
def test_context_rejections(setup,change,reason):
    order,ctx=setup
    assert reason in check_order(order,replace(ctx,**change)).reasons

def test_stale_and_expanded_spread(setup):
    order,ctx=setup
    inst=replace(ctx.instrument,quote_time=ctx.now-timedelta(seconds=20),ask=1.101)
    reasons=check_order(order,replace(ctx,instrument=inst)).reasons
    assert 'STALE_QUOTE' in reasons and 'SPREAD_TOO_WIDE' in reasons

def test_missing_stop(setup):
    order,ctx=setup
    assert 'NO_STOP_LOSS' in check_order(replace(order,stop_price=None),ctx).reasons

def test_worst_case_all_stops(setup):
    order,ctx=setup
    pos=OpenPosition('GBPUSD','GBP','USD','buy',.2,1995)
    assert 'WORST_CASE_BREACHES_DRAWDOWN_FLOOR' in check_order(order,replace(ctx,positions=[pos])).reasons

def test_live_requires_host_and_margin(setup):
    order,ctx=setup
    reasons=check_order(replace(order,strategy_status='LIVE_APPROVED'),replace(ctx,trading_mode=TradingMode.LIVE)).reasons
    assert 'LIVE_TRADING_NOT_ENABLED_ON_HOST' in reasons
    assert 'MARGIN_UNKNOWN' in reasons

def test_unprotected_position_rejects(setup):
    order,ctx=setup
    reasons=check_order(order,replace(ctx,positions=[OpenPosition('EURUSD','EUR','USD','buy',.1,None)])).reasons
    assert any(r.startswith('UNPROTECTED_OPEN_POSITION') for r in reasons)
