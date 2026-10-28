"""Clock and readiness regression checks; fake MT5 only, never a terminal call."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as N
from unittest.mock import Mock

import pytest

from qros.broker.mt5_adapter import MT5Adapter
from qros.config.schemas import RunState, TradingMode
from qros.risk.gate import GateContext, InstrumentState, OrderIntent, check_order


@pytest.fixture
def calibrated_source():
    now = [datetime(2026, 10, 23, 12, tzinfo=timezone.utc)]
    ticks = {}
    module = Mock()
    module.initialize.return_value = True
    module.terminal_info.return_value = N(connected=True, trade_allowed=False)
    module.symbol_info_tick.side_effect = lambda symbol: ticks.get(symbol)
    broker = MT5Adapter(mt5_module=module, clock=lambda: now[0])
    assert broker.connect().connected
    def update(symbol, seconds=0, offset=10800, raw=None):
        now[0] += timedelta(seconds=seconds)
        milliseconds = int((now[0].timestamp() + offset) * 1000) if raw is None else raw
        ticks[symbol] = N(time_msc=milliseconds, time=milliseconds // 1000, bid=1.1, ask=1.1002)
        return broker.quote(symbol)
    return broker, module, now, ticks, update


def establish(source):
    broker, _, _, _, update = source
    update('EURUSD')
    update('GBPUSD')
    update('EURUSD', 1)
    update('GBPUSD', 1)
    q = update('EURUSD', 1)
    assert broker.clock_verified
    return q


def test_initial_unknown_never_grants_historical_timestamp_authority(calibrated_source):
    broker, module, now, _, update = calibrated_source
    q = update('EURUSD')
    assert not broker.clock_verified
    assert q.time > now[0] + timedelta(hours=2)
    assert broker.historical_deals(now[0] - timedelta(days=1)) is None
    assert broker.completed_bars('EURUSD', 900) is None
    module.order_send.assert_not_called()


def test_three_advancing_changes_two_symbols_normalize_actual_epoch(calibrated_source):
    broker, _, now, _, _ = calibrated_source
    q = establish(calibrated_source)
    assert q.time == now[0]
    assert broker.ping().detail['observed_server_utc_offset_seconds'] == 10800
    assert broker.ping().detail['timestamp_clock_verified'] is True
    assert broker.ping().detail['terminal_trade_allowed'] is False


def test_one_symbol_cannot_self_calibrate(calibrated_source):
    broker, _, _, _, update = calibrated_source
    update('EURUSD')
    for _ in range(6):
        update('EURUSD', 1)
    assert not broker.clock_verified


def test_stale_tick_remains_old_after_reconnect(calibrated_source):
    broker, _, now, ticks, _ = calibrated_source
    fresh = establish(calibrated_source)
    frozen = ticks['EURUSD'].time_msc
    now[0] += timedelta(minutes=20)
    broker.disconnect()
    assert broker.connect().connected
    again = broker.quote('EURUSD')
    assert again.time == fresh.time and ticks['EURUSD'].time_msc == frozen
    assert (now[0] - again.time).total_seconds() == 1200


def test_unchanged_ticks_cannot_establish_nonzero_offset(calibrated_source):
    broker, _, now, _, update = calibrated_source
    update('EURUSD')
    update('GBPUSD')
    for _ in range(6):
        now[0] += timedelta(seconds=1)
        broker.quote('EURUSD')
        broker.quote('GBPUSD')
    assert not broker.clock_verified


def test_cold_start_single_utc_looking_tick_stays_unverified(calibrated_source):
    broker, _, _, _, update = calibrated_source
    update('EURUSD', offset=0)
    assert not broker.clock_verified  # could be a three-hour-old +3h broker tick


def test_backward_replayed_ticks_cannot_calibrate(calibrated_source):
    broker, _, now, ticks, update = calibrated_source
    update('EURUSD')
    update('GBPUSD')
    base = ticks['EURUSD'].time_msc
    update('EURUSD', 1, raw=base - 1000)
    update('GBPUSD', 1, raw=base - 1000)
    update('EURUSD', 1, raw=base - 2000)
    assert not broker.clock_verified


@pytest.fixture
def gate_case(firm, limits, account, spec):
    now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
    instrument = InstrumentState(spec, 'EUR', 'USD', True, 30, 1.1, 1.1001, now)
    ctx = GateContext(firm, limits, account, instrument, [], now, TradingMode.PAPER,
                      RunState.RUNNING, False, True, False, 0, 0, True, False, 1000, 30)
    return OrderIntent('EURUSD', 'buy', 1.1001, 1.0991, .1, 's1', 'PAPER_TRADING'), ctx


@pytest.mark.parametrize('field', ['entry_price', 'volume', 'stop_price', 'take_profit'])
@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_intents_fail_closed(gate_case, field, invalid):
    order, ctx = gate_case
    result = check_order(replace(order, **{field: invalid}), ctx)
    assert not result.approved and any(r.startswith('NONFINITE_OR_INVALID_DATA:') for r in result.reasons)


def test_unknown_future_or_naive_timestamps_block_gate(gate_case):
    order, ctx = gate_case
    for stamp, reason in [(None, 'NO_QUOTE'), (ctx.now + timedelta(hours=3), 'STALE_QUOTE'),
                          (ctx.now.replace(tzinfo=None), 'NAIVE_TIMESTAMP')]:
        result = check_order(order, replace(ctx, instrument=replace(ctx.instrument, quote_time=stamp)))
        assert not result.approved and reason in result.reasons


def test_invalid_contract_does_not_divide_by_zero(gate_case):
    order, ctx = gate_case
    invalid = replace(ctx.instrument.spec, volume_step=0)
    result = check_order(order, replace(ctx, instrument=replace(ctx.instrument, spec=invalid)))
    assert not result.approved and 'INVALID_CONTRACT_OR_ACCOUNT' in result.reasons


def test_readiness_free_trial_variant_and_algo_permission_stay_blocked(client):
    result = client.get('/api/system/readiness')
    assert result.status_code == 200
    state = result.json()
    checks = {c['name']: c for c in state['checks']}
    assert not checks['verified_firm_profile']['passed']
    assert not checks['terminal_algorithmic_permission']['passed']
    assert not state['ready_for_demo'] and not state['ready_for_live']
