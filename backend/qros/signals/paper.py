"""Durable paper venue. Every fill requires an observed bid/ask quote.

Call ingest_quote for each genuine upstream quote before reading the account.
The external executor must still apply check_order for strategy/firm controls.
This venue enforces local volume, protective-stop, freshness and margin checks.
Costs are explicit account-currency assumptions; fixed tick values and margin
per lot must be refreshed/validated for the account's instruments. Swap uses UTC
midnights (no triple-rollover model). No MT5 order methods are ever called.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import sqlite3
from pathlib import Path

from qros.broker.base import (AccountInfo, BrokerAdapter, BrokerOrder, BrokerPosition,
                              ConnectionStatus, OrderRequest, OrderResult, Quote, client_tag)
from qros.risk.sizing import ContractSpec


@dataclass(frozen=True)
class PaperAssumptions:
    initial_balance: float
    currency: str
    commission_per_lot_per_side: float
    adverse_slippage_points: float
    swap_long_per_lot_day: float
    swap_short_per_lot_day: float
    max_quote_age_seconds: float = 10.0


class PaperBroker(BrokerAdapter):
    name = 'paper'

    def __init__(self, path: str | Path, specs: dict[str, ContractSpec],
                 margin_per_lot: dict[str, float], assumptions: PaperAssumptions,
                 clock=lambda: datetime.now(timezone.utc)):
        self.path, self.specs, self.margins = str(path), specs, margin_per_lot
        self.assumptions, self.clock, self.connected = assumptions, clock, False
        numeric = [assumptions.initial_balance, assumptions.commission_per_lot_per_side,
                   assumptions.adverse_slippage_points, assumptions.max_quote_age_seconds,
                   assumptions.swap_long_per_lot_day, assumptions.swap_short_per_lot_day]
        if not all(math.isfinite(x) for x in numeric) or assumptions.initial_balance <= 0:
            raise ValueError('finite assumptions and positive initial balance required')
        if min(numeric[1:4]) < 0 or assumptions.max_quote_age_seconds <= 0:
            raise ValueError('costs must be nonnegative and quote age positive')
        if set(specs) != set(margin_per_lot):
            raise ValueError('explicit margin per lot required for every symbol')
        for symbol, spec in specs.items():
            values = [spec.tick_size, spec.tick_value_per_lot, spec.point, spec.volume_min,
                      spec.volume_max, spec.volume_step, margin_per_lot[symbol]]
            if symbol != spec.symbol or any(not math.isfinite(v) or v <= 0 for v in values):
                raise ValueError('invalid contract/margin specification')
        # Serialized costs/specifications prevent silent repricing on restart.
        self.config = {'assumptions': asdict(assumptions),
                       'specs': {k: asdict(v) for k, v in specs.items()}, 'margins': margin_per_lot}
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS paper_state (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO paper_state VALUES (1, ?)',
                       (json.dumps({'config': self.config, 'balance': assumptions.initial_balance,
                                    'positions': {}, 'orders': {}, 'quotes': {}, 'ids': {},
                                    'deals': [], 'sequence': 0}),))
        with self._state() as state:
            if state['config'] != self.config:
                raise ValueError('paper configuration differs from persisted account; use a new account database')

    @contextmanager
    def _state(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute('BEGIN IMMEDIATE')
            state = json.loads(db.execute('SELECT value FROM paper_state WHERE id=1').fetchone()[0])
            yield state
            db.execute('UPDATE paper_state SET value=? WHERE id=1', (json.dumps(state, allow_nan=False),))
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def connect(self):
        self.connected = True
        return ConnectionStatus(True, {'paper': True, 'cost_assumptions': asdict(self.assumptions)})

    def disconnect(self):
        self.connected = False

    def ping(self):
        return ConnectionStatus(self.connected, {'paper': True})

    def _fresh(self, q):
        if q is None:
            return False
        age = (self.clock() - datetime.fromisoformat(q['time'])).total_seconds()
        return 0 <= age <= self.assumptions.max_quote_age_seconds

    def quote(self, symbol):
        with self._state() as s:
            q = s['quotes'].get(symbol)
            return Quote(symbol, q['bid'], q['ask'], datetime.fromisoformat(q['time'])) if q else None

    def contract_spec(self, symbol):
        return self.specs.get(symbol)

    def margin_required(self, symbol, side, volume, price):
        return self.margins[symbol] * volume if symbol in self.margins else None

    def _pnl(self, p, q):
        current = q['bid'] if p['side'] == 'buy' else q['ask']
        sign = 1 if p['side'] == 'buy' else -1
        spec = self.specs[p['symbol']]
        return sign * (current - p['price']) / spec.tick_size * spec.tick_value_per_lot * p['volume']

    def _account(self, s):
        equity = s['balance'] + sum(self._pnl(p, s['quotes'][p['symbol']]) for p in s['positions'].values())
        margin = sum(self.margins[p['symbol']] * p['volume']
                     for group in ('positions', 'orders') for p in s[group].values())
        return AccountInfo('paper', 'isolated-paper-ledger', True, self.assumptions.currency,
                           s['balance'], equity, margin, equity - margin, None, self.connected)

    def account_info(self):
        if not self.connected:
            return None
        with self._state() as s:
            return self._account(s)

    def positions(self):
        if not self.connected:
            return None
        with self._state() as s:
            return [BrokerPosition(t, p['symbol'], p['side'], p['volume'], p['price'],
                                   s['quotes'][p['symbol']]['bid' if p['side'] == 'buy' else 'ask'],
                                   p['sl'], p['tp'], self._pnl(p, s['quotes'][p['symbol']]),
                                   p['magic'], client_tag(p['client_order_id']), datetime.fromisoformat(p['time']))
                    for t, p in s['positions'].items()]

    def pending_orders(self):
        if not self.connected:
            return None
        with self._state() as s:
            return [BrokerOrder(t, p['symbol'], p['side'] + '_limit', p['volume'], p['limit'],
                                p['sl'], p['tp'], client_tag(p['client_order_id']))
                    for t, p in s['orders'].items()]

    def realized_pnl_since(self, since):
        with self._state() as s:
            return sum(d['net'] for d in s['deals'] if datetime.fromisoformat(d['time']) >= since)

    def find_client_order(self, client_order_id):
        with self._state() as s:
            return s['ids'].get(client_order_id)

    def _validate(self, s, req, price):
        if not self.connected:
            return 'PAPER_DISCONNECTED'
        spec = self.specs.get(req.symbol)
        values = [req.volume, req.sl, price] + ([req.tp] if req.tp is not None else [])
        if not spec or not req.client_order_id or req.side not in ('buy', 'sell'):
            return 'INVALID_ORDER'
        if any(not math.isfinite(v) or v <= 0 for v in values):
            return 'INVALID_PRICE_VOLUME'
        if not self._fresh(s['quotes'].get(req.symbol)):
            return 'QUOTE_STALE_OR_UNKNOWN'
        steps = req.volume / spec.volume_step
        if not spec.volume_min <= req.volume <= spec.volume_max or abs(steps - round(steps)) > 1e-7:
            return 'INVALID_VOLUME'
        sign = 1 if req.side == 'buy' else -1
        if sign * (price - req.sl) <= 0 or sign * (price - req.sl) < spec.min_stop_points * spec.point:
            return 'INVALID_PROTECTIVE_STOP'
        if req.tp is not None and sign * (req.tp - price) <= 0:
            return 'INVALID_TAKE_PROFIT'
        required = self.margins[req.symbol] * req.volume + self.assumptions.commission_per_lot_per_side * req.volume
        if self._account(s).free_margin < required:
            return 'INSUFFICIENT_MARGIN'
        return None

    def _entry_price(self, req, q):
        slip = self.assumptions.adverse_slippage_points * self.specs[req.symbol].point
        return q['ask'] + slip if req.side == 'buy' else q['bid'] - slip

    def _fill(self, s, ticket, p, price, at):
        p = dict(p, price=price, time=at, swap_date=at[:10])
        s['positions'][ticket] = p
        cost = self.assumptions.commission_per_lot_per_side * p['volume']
        s['balance'] -= cost
        s['deals'].append({'ticket': ticket, 'kind': 'entry', 'time': at, 'net': -cost, 'price': price,
                           'symbol': p['symbol'], 'side': p['side'], 'volume': p['volume'],
                           'sl': p['sl'], 'tp': p['tp'], 'client_order_id': p['client_order_id'],
                           'magic': p['magic'], 'commission': -cost, 'swap': 0, 'profit': 0})

    def _submit(self, req, limit=None):
        with self._state() as s:
            if req.client_order_id in s['ids']:
                return OrderResult(False, ticket=s['ids'][req.client_order_id], duplicate=True, message='DUPLICATE')
            q = s['quotes'].get(req.symbol)
            price = limit if limit is not None else (self._entry_price(req, q) if q and req.symbol in self.specs else 0)
            error = self._validate(s, req, price)
            if error:
                return OrderResult(False, message=error, details={'outcome': 'not_submitted'})
            s['sequence'] += 1
            ticket = 'P' + str(s['sequence'])
            s['ids'][req.client_order_id] = ticket
            p = asdict(req)
            if limit is not None:
                p['limit'] = limit
                s['orders'][ticket] = p
                return OrderResult(True, ticket=ticket, message='PAPER_LIMIT_ACCEPTED', verified=True)
            self._fill(s, ticket, p, price, q['time'])
            return OrderResult(True, ticket=ticket, fill_price=price, filled_volume=req.volume, verified=True)

    def send_market_order(self, req):
        return self._submit(req)

    def send_limit_order(self, req, limit_price):
        return self._submit(req, limit_price)

    def _close(self, s, ticket, reason):
        p = s['positions'][ticket]
        q = s['quotes'][p['symbol']]
        slip = self.assumptions.adverse_slippage_points * self.specs[p['symbol']].point
        exit_q = dict(q)
        exit_q['bid' if p['side'] == 'buy' else 'ask'] += -slip if p['side'] == 'buy' else slip
        price = exit_q['bid' if p['side'] == 'buy' else 'ask']
        net = self._pnl(p, exit_q) - self.assumptions.commission_per_lot_per_side * p['volume']
        s['balance'] += net
        commission = self.assumptions.commission_per_lot_per_side * p['volume']
        s['deals'].append({'ticket': ticket, 'kind': reason, 'time': q['time'], 'net': net, 'price': price,
                           'symbol': p['symbol'], 'side': p['side'], 'volume': p['volume'],
                           'sl': p['sl'], 'tp': p['tp'], 'client_order_id': p['client_order_id'],
                           'magic': p['magic'], 'commission': -commission, 'swap': 0, 'profit': net + commission})
        del s['positions'][ticket]
        return OrderResult(True, ticket=ticket, fill_price=price, filled_volume=p['volume'], verified=True)

    def close_position(self, ticket):
        with self._state() as s:
            p = s['positions'].get(ticket)
            if not self.connected or p is None or not self._fresh(s['quotes'].get(p['symbol'])):
                return OrderResult(False, message='POSITION_UNKNOWN_DISCONNECTED_OR_STALE', details={'outcome': 'not_submitted'})
            return self._close(s, ticket, 'manual_close')

    def cancel_order(self, ticket):
        with self._state() as s:
            if not self.connected or ticket not in s['orders']:
                return OrderResult(False, message='ORDER_UNKNOWN_OR_DISCONNECTED', details={'outcome': 'not_submitted'})
            del s['orders'][ticket]
            return OrderResult(True, ticket=ticket, verified=True)

    def ingest_quote(self, quote: Quote):
        if quote.time.tzinfo is None or quote.symbol not in self.specs:
            raise ValueError('known symbol and timezone-aware quote required')
        if not all(math.isfinite(v) and v > 0 for v in (quote.bid, quote.ask)) or quote.ask < quote.bid:
            raise ValueError('invalid quote')
        q = {'bid': quote.bid, 'ask': quote.ask, 'time': quote.time.astimezone(timezone.utc).isoformat()}
        if not self._fresh(q):
            raise ValueError('stale/future quote')
        with self._state() as s:
            old = s['quotes'].get(quote.symbol)
            if old and q['time'] <= old['time']:
                return False
            s['quotes'][quote.symbol] = q
            for ticket, p in list(s['positions'].items()):
                if p['symbol'] != quote.symbol:
                    continue
                days = (quote.time.astimezone(timezone.utc).date() - datetime.fromisoformat(p['swap_date']).date()).days
                if days > 0:
                    rate = (self.assumptions.swap_long_per_lot_day if p['side'] == 'buy'
                            else self.assumptions.swap_short_per_lot_day)
                    swap = days * rate * p['volume']
                    s['balance'] += swap
                    p['swap_date'] = q['time'][:10]
                    s['deals'].append({'ticket': ticket, 'kind': 'swap', 'time': q['time'], 'net': swap,
                                       'symbol': p['symbol'], 'side': p['side'], 'volume': p['volume'],
                                       'client_order_id': p['client_order_id'],
                                       'magic': p['magic'], 'commission': 0, 'swap': swap, 'profit': 0})
                price = quote.bid if p['side'] == 'buy' else quote.ask
                sign = 1 if p['side'] == 'buy' else -1
                if sign * (price - p['sl']) <= 0:
                    self._close(s, ticket, 'stop_loss')
                elif p['tp'] is not None and sign * (price - p['tp']) >= 0:
                    self._close(s, ticket, 'take_profit')
            for ticket, p in list(s['orders'].items()):
                if p['symbol'] != quote.symbol:
                    continue
                reached = quote.ask <= p['limit'] if p['side'] == 'buy' else quote.bid >= p['limit']
                if not reached:
                    continue
                del s['orders'][ticket]
                req = OrderRequest(**{k: v for k, v in p.items() if k != 'limit'})
                price = self._entry_price(req, q)
                # A limit never executes worse than its limit; no unobserved improvement.
                price = min(price, p['limit']) if p['side'] == 'buy' else max(price, p['limit'])
                error = self._validate(s, req, price)
                if error:
                    s['deals'].append({'ticket': ticket, 'kind': 'limit_rejected_at_trigger',
                                       'time': q['time'], 'net': 0, 'reason': error})
                    continue
                self._fill(s, ticket, p, price, q['time'])
            return True

    def ledger(self):
        with self._state() as s:
            return list(s['deals'])

    def historical_deals(self, since):
        """Actual simulated executions/cost events, never inferred synthetic fills."""
        with self._state() as s:
            result = []
            for index, d in enumerate(s['deals']):
                if datetime.fromisoformat(d['time']) < since or d['kind'] == 'limit_rejected_at_trigger':
                    continue
                stamp = datetime.fromisoformat(d['time']).timestamp()
                is_entry, is_swap = d['kind'] == 'entry', d['kind'] == 'swap'
                side = d['side'] if is_entry else ('sell' if d['side'] == 'buy' else 'buy')
                result.append(dict(d, ticket='PD' + str(index + 1), position_id=d['ticket'],
                                   deal_id='PD' + str(index + 1), position_ticket=d['ticket'], source='paper',
                                   time=int(stamp), time_msc=int(stamp * 1000), type=0 if side == 'buy' else 1,
                                   entry=0 if is_entry or is_swap else 1,
                                   volume=0 if is_swap else d['volume'], price=d.get('price', 0),
                                   profit=d.get('profit', 0), commission=d.get('commission', 0),
                                   swap=d.get('swap', 0), fee=0, magic=d.get('magic', 770001),
                                   comment=client_tag(d['client_order_id'])))
            return result


class PaperMarketAdapter(BrokerAdapter):
    """Observed market reads from source; all account and order writes stay paper.

    The source account and its existing positions are never read or modified.
    Contract values in the paper ledger remain declared simulation assumptions;
    source margin is an additional conservative check, never a substitute for
    the executor's firm/strategy risk gate.
    """
    name = 'paper'

    def __init__(self, source: BrokerAdapter, paper: PaperBroker, symbols=None):
        self.source, self.paper = source, paper
        self.symbols = list(symbols if symbols is not None else paper.specs)
        self.observed_specs = {}
        self.observed_margin_per_lot = {}
        self.ready = False
        self.last_status = ConnectionStatus(False, error='NOT_CONNECTED')

    def connect(self):
        status = self.source.connect()
        if not status.connected:
            self.ready = False
            self.last_status = status
            return status
        self.paper.connect()
        return self.refresh_quotes()

    def disconnect(self):
        self.ready = False
        self.paper.disconnect()
        self.source.disconnect()

    def refresh_quotes(self):
        try:
            if not self.symbols:
                raise ValueError('NO_ENABLED_PAPER_SYMBOLS')
            for symbol in self.symbols:
                observed = self.source.contract_spec(symbol)
                configured = self.paper.contract_spec(symbol)
                if observed is None or configured is None:
                    raise ValueError('CONTRACT_SPEC_UNKNOWN:' + symbol)
                structural = ('point', 'tick_size', 'volume_min', 'volume_max', 'volume_step', 'min_stop_points')
                if any(not math.isclose(getattr(observed, field), getattr(configured, field), rel_tol=1e-8)
                       for field in structural):
                    raise ValueError('CONTRACT_SPEC_CHANGED:' + symbol)
                q = self.source.quote(symbol)
                if q is None:
                    raise ValueError('QUOTE_UNKNOWN:' + symbol)
                # Both directions can have different margin; reserve the larger.
                margins = [self.source.margin_required(symbol, side, 1.0, price)
                           for side, price in [('buy', q.ask), ('sell', q.bid)]]
                if any(m is None or not math.isfinite(m) or m <= 0 for m in margins):
                    raise ValueError('MARGIN_UNKNOWN:' + symbol)
                self.observed_specs[symbol] = observed
                self.observed_margin_per_lot[symbol] = max(margins)
                self.paper.ingest_quote(q)
            self.ready = True
            self.last_status = ConnectionStatus(True, {'paper': True, 'quote_source': self.source.name,
                                                       'symbols': self.symbols,
                                                       'fixed_tick_value_assumption': True,
                                                       'cost_assumptions': asdict(self.paper.assumptions)})
        except (ValueError, TypeError, ArithmeticError) as e:
            self.ready = False
            self.last_status = ConnectionStatus(False, {'paper': True}, str(e))
        return self.last_status

    def ping(self):
        status = self.source.ping()
        if not status.connected:
            self.ready = False
            self.last_status = status
            return status
        return self.refresh_quotes()

    def account_info(self):
        if not self.ready:
            return None
        account = self.paper.account_info()
        positions, orders = self.paper.positions(), self.paper.pending_orders()
        if account is None or positions is None or orders is None:
            return None
        margin = sum(max(self.observed_margin_per_lot.get(p.symbol, 0), self.paper.margins[p.symbol]) * p.volume
                     for p in positions + orders)
        return AccountInfo(account.login, account.server, True, account.currency, account.balance,
                           account.equity, margin, account.equity - margin, None, self.ready)

    def positions(self):
        return self.paper.positions() if self.ready else None

    def pending_orders(self):
        return self.paper.pending_orders() if self.ready else None

    def quote(self, symbol):
        return self.paper.quote(symbol) if self.ready and symbol in self.symbols else None

    def contract_spec(self, symbol):
        # Paper P/L uses an explicitly fixed tick-value assumption.
        return self.paper.contract_spec(symbol) if symbol in self.observed_specs else None

    def margin_required(self, symbol, side, volume, price):
        if symbol not in self.observed_margin_per_lot:
            return None
        return max(self.observed_margin_per_lot[symbol], self.paper.margins[symbol]) * volume

    def realized_pnl_since(self, since):
        return self.paper.realized_pnl_since(since)

    def find_client_order(self, client_order_id):
        return self.paper.find_client_order(client_order_id)

    def _margin_check(self, req):
        if not self.ready or req.symbol not in self.symbols:
            return 'PAPER_MARKET_NOT_READY'
        account = self.account_info()
        required = self.margin_required(req.symbol, req.side, req.volume, 0)
        if account is None or required is None:
            return 'MARGIN_UNKNOWN'
        if account.free_margin < required + self.paper.assumptions.commission_per_lot_per_side * req.volume:
            return 'INSUFFICIENT_OBSERVED_MARGIN'
        return None

    def send_market_order(self, req):
        error = self._margin_check(req)
        return OrderResult(False, message=error, details={'outcome': 'not_submitted'}) if error else self.paper.send_market_order(req)

    def send_limit_order(self, req, limit_price):
        error = self._margin_check(req)
        return OrderResult(False, message=error, details={'outcome': 'not_submitted'}) if error else self.paper.send_limit_order(req, limit_price)

    def cancel_order(self, ticket):
        return self.paper.cancel_order(ticket)

    def close_position(self, ticket):
        return self.paper.close_position(ticket) if self.ready else OrderResult(False, message='PAPER_MARKET_NOT_READY', details={'outcome': 'not_submitted'})

    def historical_deals(self, since):
        return self.paper.historical_deals(since)

    def completed_bars(self, symbol, timeframe_seconds, count):
        return self.source.completed_bars(symbol, timeframe_seconds, count)
