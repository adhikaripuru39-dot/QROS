import pytest
from qros.backtest import Bar, Signal, BacktestConfig, BacktestEngine


def bar(t, op=100, hi=101, lo=99, close=100, spread=1):
    return Bar(t, op, hi, lo, close, spread)


def config(**kwargs):
    return BacktestConfig(contract_size=1, commission_per_lot_side=0, min_lot=1, lot_step=1, **kwargs)


def test_next_bar_execution_and_no_future_history():
    seen = []
    def strategy(history):
        seen.append(tuple(b.time for b in history))
        return Signal(1, 1, 50, 50)
    result = BacktestEngine().run([bar(0), bar(60, 110, 112, 109, 111)], strategy, config())
    assert seen == [(0,)]
    assert result.trades[0].entry_time == 60
    assert result.trades[0].entry == 111
    assert result.final_cash == 10000


def test_ambiguous_bar_stop_precedes_profitable_target():
    result = BacktestEngine().run([bar(0), bar(60, 100, 120, 80)],
        lambda _: Signal(1, 1, 10, 10), config())
    assert result.trades[0].reason == "stop"
    assert result.trades[0].net_pnl == -10


def test_gap_stop_fills_worse_open_and_costs():
    result = BacktestEngine().run([bar(0), bar(60), bar(86460, 80, 81, 79, 80)],
        lambda _: Signal(1, 1, 10, 100),
        BacktestConfig(contract_size=1, min_lot=1, lot_step=1,
                       commission_per_lot_side=2, slippage=.5, swap_per_lot_day=3))
    trade = result.trades[0]
    assert trade.exit == 79.5
    assert trade.entry == 101.5
    assert trade.net_pnl == -29
    assert result.final_cash == 9971


def test_short_uses_ask_for_exit():
    result = BacktestEngine().run([bar(0), bar(60)], lambda _: Signal(-1, 1, 50, 50), config())
    assert result.trades[0].net_pnl == -1


def test_margin_and_volume_reject_before_entry():
    engine = BacktestEngine()
    assert engine.run([bar(0), bar(60)], lambda _: Signal(1, .5, 50, 50), config()).rejected[0]["reason"] == "volume"
    assert engine.run([bar(0), bar(60)], lambda _: Signal(1, 100, 50, 50), config(initial_cash=100)).rejected[0]["reason"] == "insufficient_margin"


def test_bad_input_and_zero_spread_is_explicit_valid():
    with pytest.raises(ValueError):
        BacktestEngine().run([bar(0), bar(0)], lambda _: None)
    with pytest.raises(ValueError):
        BacktestEngine().run([bar(0, spread=float("nan"))], lambda _: None)
    assert BacktestEngine().run([bar(0, spread=0)], lambda _: None).final_cash == 10000


def test_margin_liquidation_is_conservative():
    result = BacktestEngine().run([bar(0), bar(60, 100, 101, 50, 100, 0)],
        lambda _: Signal(1, 10, 100, 100), config(initial_cash=1000, leverage=1))
    assert result.trades[0].reason == "margin_liquidation"
    assert result.final_cash == 500
