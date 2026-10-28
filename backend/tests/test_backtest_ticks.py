from datetime import datetime, timezone
import pytest
from qros.backtest import Bar,Tick,Signal,BacktestEngine,BacktestConfig,RolloverSchedule,SwapRecord,CostRecord


def cfg(**kwargs): return BacktestConfig(contract_size=1,commission_per_lot_side=0,min_lot=1,lot_step=1,**kwargs)
def bars(): return [Bar(0,100,101,99,100,1),Bar(60,100,120,80,100,1),Bar(120,100,101,99,100,1)]


def test_observed_target_before_stop_overrides_bar_ambiguity_without_future_leak():
    seen=[]
    def strategy(history):
        seen.append([b.time for b in history]); return Signal(1,1,10,10)
    ticks=[Tick(60000,100,101),Tick(70000,112,113),Tick(80000,80,81)]
    result=BacktestEngine().run_ticks(bars(),ticks,strategy,cfg())
    assert result.trades[0].reason=="target"
    assert result.trades[0].entry_time==60 and result.trades[0].exit_time==70
    assert seen==[[0]]
    assert result.trades[0].net_pnl==11
    assert not result.live_eligible


def test_real_quote_gap_and_short_ask_trigger():
    ticks=[Tick(60000,100,101),Tick(70000,120,121)]
    result=BacktestEngine().run_ticks(bars(),ticks,lambda _:Signal(-1,1,10,10),cfg())
    assert result.trades[0].exit==121 and result.trades[0].net_pnl==-21


def test_sentinel_excludes_future_ticks_and_missing_quotes_reject():
    result=BacktestEngine().run_ticks(bars(),[Tick(130000,100,101)],lambda _:Signal(1,1,10,10),cfg())
    assert not result.trades and result.rejected[0]["reason"]=="missing_execution_quotes"


def test_cost_availability_and_observed_swap_records():
    result=BacktestEngine().run_ticks(bars(),[Tick(60000,100,101),Tick(70000,100,101)],
        lambda _:Signal(1,1,10,10),cfg(),
        cost_records=[CostRecord(60000,2,"deal-a"),CostRecord(65000,3,"deal-b"),CostRecord(80000,100,"future")],
        swap_records=[SwapRecord(65000,4,"swap-ledger"),SwapRecord(80000,100,"future")])
    assert result.trades[0].commission==5
    assert result.trades[0].swap==4
    assert result.final_cash==9990


def test_broker_rollover_triple_swap_and_timezone():
    def ms(iso): return int(datetime.fromisoformat(iso).timestamp()*1000)
    schedule=RolloverSchedule(timezone="Europe/Athens",hour=0,triple_weekday=2,long_debit_per_lot=2)
    # Athens midnight Wednesday is Tuesday 22:00 UTC in January.
    assert schedule.debit(ms("2026-01-06T21:59:00+00:00"),ms("2026-01-06T22:01:00+00:00"),1,1)==6
    with pytest.raises(ValueError): RolloverSchedule(hour=25).debit(0,1,1,1)


def test_size_and_volatility_slippage_uses_completed_bar_only():
    result=BacktestEngine().run_ticks(bars(),[Tick(60000,100,101),Tick(70000,100,101)],
        lambda _:Signal(1,2,50,50),cfg(slippage_per_lot=.5,slippage_volatility_fraction=.25))
    # Prior completed range=2; current parent range=40 must not influence entry.
    assert result.trades[0].entry==102.5
    assert result.trades[0].exit==98.5


def test_ticks_preserve_equal_timestamp_source_order_and_reject_disorder():
    result=BacktestEngine().run_ticks(bars(),[Tick(60000,100,101),Tick(60000,112,113),Tick(60000,80,81)],
        lambda _:Signal(1,1,10,10),cfg())
    assert result.trades[0].reason=="target"
    with pytest.raises(ValueError):
        BacktestEngine().run_ticks(bars(),[Tick(70000,100,101),Tick(60000,100,101)],lambda _:None,cfg())
