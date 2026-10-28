from datetime import datetime, timedelta, timezone

import pytest

from qros.broker.base import OrderRequest, Quote, client_tag
from qros.risk.sizing import ContractSpec
from qros.signals.paper import PaperAssumptions, PaperBroker


@pytest.fixture
def venue(tmp_path):
    now = [datetime(2026, 10, 22, 12, tzinfo=timezone.utc)]
    spec = ContractSpec('EURUSD', .0001, 10, .0001, .01, 10, .01)
    assumptions = PaperAssumptions(10000, 'USD', 3, 1, -2, -1)
    path = tmp_path / 'paper.sqlite'
    def create():
        b = PaperBroker(path, {'EURUSD': spec}, {'EURUSD': 1000}, assumptions, lambda: now[0])
        b.connect()
        return b
    return create, now


def tick(b, now, bid=1.1000, ask=1.1002):
    b.ingest_quote(Quote('EURUSD', bid, ask, now[0]))


def req(cid='one', side='buy', volume=.1, sl=1.09, tp=None):
    return OrderRequest(cid, 'EURUSD', side, volume, sl, tp)


def test_no_fill_without_actual_quote_or_with_stale_quote(venue):
    create, now = venue
    b = create()
    assert not b.send_market_order(req()).ok
    tick(b, now)
    now[0] += timedelta(seconds=11)
    assert not b.send_market_order(req()).ok
    assert not b.positions()


def test_bid_ask_cost_accounting_restart_and_dedup(venue):
    create, now = venue
    b = create()
    tick(b, now)
    fill = b.send_market_order(req())
    assert fill.ok and fill.fill_price == pytest.approx(1.1003)
    assert b.positions()[0].profit == pytest.approx(-3)
    assert b.account_info().balance == pytest.approx(9999.7)
    b = create()
    assert b.find_client_order('one') == fill.ticket
    assert b.send_market_order(req()).duplicate
    closed = b.close_position(fill.ticket)
    assert closed.fill_price == pytest.approx(1.0999)
    assert b.account_info().balance == pytest.approx(9995.4)
    assert b.realized_pnl_since(now[0] - timedelta(seconds=1)) == pytest.approx(-4.6)
    assert b.send_market_order(req()).duplicate  # closed deals stay deduplicated


def test_gap_stop_uses_observed_executable_price(venue):
    create, now = venue
    b = create()
    tick(b, now)
    b.send_market_order(req(sl=1.099))
    now[0] += timedelta(seconds=1)
    tick(b, now, 1.095, 1.0952)
    assert not b.positions()
    assert b.ledger()[-1]['kind'] == 'stop_loss'
    assert b.ledger()[-1]['price'] == pytest.approx(1.0949)


def test_sell_values_and_triggers_on_ask(venue):
    create, now = venue
    b = create()
    tick(b, now)
    b.send_market_order(req(side='sell', sl=1.101))
    assert b.positions()[0].profit == pytest.approx(-3)
    now[0] += timedelta(seconds=1)
    tick(b, now, 1.1008, 1.1011)
    assert not b.positions()
    assert b.ledger()[-1]['price'] == pytest.approx(1.1012)


def test_limits_wait_for_observed_cross_and_survive_restart(venue):
    create, now = venue
    b = create()
    tick(b, now)
    result = b.send_limit_order(req(sl=1.09), 1.099)
    assert result.ok and len(b.pending_orders()) == 1 and not b.positions()
    b = create()
    now[0] += timedelta(seconds=1)
    tick(b, now, 1.0987, 1.0989)
    assert not b.pending_orders()
    assert b.positions()[0].price_open <= 1.099


def test_margin_reserves_pending_and_invalid_stops_reject(venue):
    create, now = venue
    b = create()
    tick(b, now)
    assert not b.send_market_order(req(sl=1.2)).ok
    assert not b.send_market_order(req(volume=.015)).ok
    assert not b.send_market_order(req(volume=10)).ok
    assert b.send_limit_order(req(volume=9), 1.099).ok
    assert not b.send_market_order(req(cid='two', volume=2)).ok


def test_swap_no_duplicate_rollover_or_out_of_order_quote(venue):
    create, now = venue
    b = create()
    tick(b, now)
    b.send_market_order(req())
    now[0] += timedelta(days=1)
    tick(b, now)
    assert b.account_info().balance == pytest.approx(9999.5)
    assert not b.ingest_quote(Quote('EURUSD', 1.1, 1.1002, now[0]))
    assert len([d for d in b.ledger() if d['kind'] == 'swap']) == 1


def test_reject_nan_inverted_future_quotes(venue):
    create, now = venue
    b = create()
    for bid, ask, at in [(float('nan'), 1.1, now[0]), (1.2, 1.1, now[0]),
                         (1.1, 1.2, now[0] + timedelta(seconds=1))]:
        with pytest.raises(ValueError):
            b.ingest_quote(Quote('EURUSD', bid, ask, at))


def test_market_wrapper_cannot_send_real_orders_and_normalizes_deals(venue):
    from unittest.mock import Mock
    from qros.broker.base import ConnectionStatus
    from qros.signals.paper import PaperMarketAdapter
    create, now = venue
    paper = create()
    source = Mock()
    source.name = 'read-only-test-source'
    source.connect.return_value = ConnectionStatus(True)
    source.ping.return_value = ConnectionStatus(True)
    source.contract_spec.return_value = paper.specs['EURUSD']
    source.quote.return_value = Quote('EURUSD', 1.1, 1.1002, now[0])
    source.margin_required.return_value = 1500
    source.completed_bars.return_value = [{'time': 1, 'open': 1.1}]
    wrapper = PaperMarketAdapter(source, paper)
    assert wrapper.connect().connected
    fill = wrapper.send_market_order(req())
    assert fill.ok
    assert wrapper.account_info().margin == 150
    assert wrapper.margin_required('EURUSD', 'buy', 1, 1.1) == 1500
    assert wrapper.completed_bars('EURUSD', 60, 10) == source.completed_bars.return_value
    assert wrapper.close_position(fill.ticket).ok
    deals = wrapper.historical_deals(now[0] - timedelta(seconds=1))
    assert len(deals) == 2 and [d['entry'] for d in deals] == [0, 1]
    assert deals[0]['position_id'] == fill.ticket and deals[1]['type'] == 1
    assert deals[0]['comment'] == client_tag('one')
    assert sum(d['profit'] + d['commission'] + d['swap'] + d['fee'] for d in deals) == pytest.approx(-4.6)
    for method in ['send_market_order', 'close_position', 'cancel_order', 'account_info', 'positions']:
        getattr(source, method).assert_not_called()
    now[0] += timedelta(seconds=30)
    assert not wrapper.ping().connected
    assert wrapper.positions() is None
    assert not wrapper.send_market_order(req(cid='second')).ok


def test_wrapper_unknown_margin_fails_closed(venue):
    from unittest.mock import Mock
    from qros.broker.base import ConnectionStatus
    from qros.signals.paper import PaperMarketAdapter
    create, now = venue
    paper = create()
    source = Mock()
    source.connect.return_value = ConnectionStatus(True)
    source.contract_spec.return_value = paper.specs['EURUSD']
    source.quote.return_value = Quote('EURUSD', 1.1, 1.1002, now[0])
    source.margin_required.return_value = None
    wrapper = PaperMarketAdapter(source, paper)
    assert not wrapper.connect().connected
    assert wrapper.account_info() is None
