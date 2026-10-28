from dataclasses import replace
from datetime import datetime, timedelta, timezone

from qros.broker.base import Quote
from qros.risk.sizing import ContractSpec
from qros.signals.engine import Bar, SignalEngine, StrategyRuntime, completed_bars


def setup():
    now = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
    bars = [Bar(now - timedelta(minutes=70 - i), 1.1, 1.101, 1.099, 1.1, 100) for i in range(71)]
    strategy = StrategyRuntime('s1', 'momentum', 'EURUSD', 'PAPER_TRADING', 60, 50, enabled=True)
    quote = Quote('EURUSD', 1.1, 1.1002, now)
    spec = ContractSpec('EURUSD', .0001, 10, .0001, .01, 10, .01)
    return now, bars, strategy, quote, spec


def test_completed_only_and_deterministic_id_next_observation():
    now, bars, strategy, q, spec = setup()
    seen = []
    def evaluator(records, strategy_id, context_bars=None):
        seen.append(records)
        return [1] * len(records)
    e = SignalEngine(evaluator=evaluator)
    first = e.evaluate(strategy, {60: bars}, q, now, spec)
    assert first.intent is not None
    assert seen[0][-1]['time'] == now
    assert len(seen[0]) == 70  # forming final bar excluded
    assert first.intent.entry_price == q.ask
    again = SignalEngine(evaluator=evaluator).evaluate(strategy, {60: bars}, q, now, spec)
    assert first.client_order_id == again.client_order_id
    bars[-1] = replace(bars[-1], close=1.5, high=1.5)
    assert e.evaluate(strategy, {60: bars}, q, now, spec).intent == first.intent


def test_no_default_activation_and_status_guard():
    now, bars, s, q, spec = setup()
    engine = SignalEngine()
    assert engine.evaluate(replace(s, enabled=False), {60: bars}, q, now, spec).reason == 'STRATEGY_DISABLED'
    assert engine.evaluate(replace(s, strategy_status='RESEARCH_ONLY'), {60: bars}, q, now, spec).intent is None


def test_stale_quotes_gaps_and_incomplete_mtf_fail_closed():
    now, bars, s, q, spec = setup()
    e = SignalEngine(evaluator=lambda records, sid, **kw: [1] * len(records))
    assert e.evaluate(s, {60: bars}, replace(q, time=now - timedelta(seconds=20)), now, spec).intent is None
    assert e.evaluate(s, {60: bars[:40] + bars[41:]}, q, now, spec).reason == 'BAR_HISTORY_GAP'
    assert e.evaluate(replace(s, hypothesis_id='multi_timeframe'), {60: bars}, q, now, spec).intent is None


def test_h4_forming_bar_excluded():
    now, bars, s, q, spec = setup()
    h4 = [Bar(now - timedelta(hours=84 - 4 * i), 1.1, 1.101, 1.099, 1.1) for i in range(22)]
    seen = []
    def evaluator(records, sid, context_bars=None):
        seen.extend(context_bars['H4'])
        return [1] * len(records)
    result = SignalEngine(evaluator=evaluator).evaluate(replace(s, hypothesis_id='multi_timeframe'),
                                                       {60: bars, 14400: h4}, q, now, spec)
    assert result.intent is not None
    assert len(seen) == 21 and max(b['close_time'] for b in seen) == now
