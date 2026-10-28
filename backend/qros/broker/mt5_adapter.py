"""MetaTrader 5 adapter (Windows only; requires a running MT5 terminal).

Notes on MT5 semantics handled here:
* The Python API documents tick/deal timestamps as UTC epoch seconds.
  Use broker tick timestamps for staleness; never make an old tick fresh on reconnect.
* ``order_send`` returning a DONE retcode is not treated as success until the
  resulting position is observed via ``positions_get`` (verification).
* Duplicate protection: each order carries ``client_tag(client_order_id)`` in
  its comment; before sending we search open positions, pending orders and
  recent deals for that tag.

STATUS: logic covered by unit tests against a fake MetaTrader5 module.
Not yet verified against a real terminal in this environment.
"""
from __future__ import annotations

import time as _time
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from qros.risk.sizing import ContractSpec

from .base import (AccountInfo, BrokerAdapter, BrokerOrder, BrokerPosition, ConnectionStatus,
                   OrderRequest, OrderResult, Quote, client_tag)

RET_DONE = 10009
RET_PLACED = 10008
RET_DONE_PARTIAL = 10010
OK_RETCODES = {RET_DONE, RET_PLACED, RET_DONE_PARTIAL}
ACCOUNT_TRADE_MODE_DEMO = 0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MT5Adapter(BrokerAdapter):
    name = "mt5"

    def __init__(self, path: Optional[str] = None, login: Optional[int] = None,
                 password: Optional[str] = None, server: Optional[str] = None,
                 mt5_module: Any = None, verify_attempts: int = 5, verify_sleep: float = 0.2,
                 clock=_utcnow, allow_orders: bool = False):
        self._path, self._login, self._password, self._server = path, login, password, server
        self.allow_orders = allow_orders
        self._mt5 = mt5_module
        self._import_error: Optional[str] = None
        if self._mt5 is None:
            try:
                import MetaTrader5 as mt5  # type: ignore
                self._mt5 = mt5
            except Exception as e:  # pragma: no cover - environment dependent
                self._import_error = f"MetaTrader5 package unavailable: {e}"
        self._initialized = False
        self._verify_attempts = verify_attempts
        self._verify_sleep = verify_sleep
        self._clock = clock
        self._tick_seen: dict[str, tuple[int, datetime]] = {}
        self._clock_samples = []
        self._utc_offset_seconds = None
        self.clock_verified = False

    # ---- connection ------------------------------------------------------
    def _err(self) -> str:
        try:
            code, msg = self._mt5.last_error()
            return f"{code}: {msg}"
        except Exception:
            return "unknown MT5 error"

    def connect(self) -> ConnectionStatus:
        if self._mt5 is None:
            return ConnectionStatus(False, {"adapter": "mt5"}, self._import_error)
        kwargs: dict[str, Any] = {}
        if self._path:
            kwargs["path"] = self._path
        if self._login:
            kwargs.update(login=int(self._login), password=self._password or "", server=self._server or "")
        kwargs["timeout"] = 15000
        ok = self._mt5.initialize(**kwargs)
        self._initialized = bool(ok)
        if not ok:
            return ConnectionStatus(False, {"adapter": "mt5"}, f"initialize failed: {self._err()}")
        account=self._mt5.account_info()
        self._expected_identity=(str(account.server),str(account.login)) if account is not None else None
        return self.ping()

    def disconnect(self) -> None:
        if self._mt5 is not None and self._initialized:
            self._mt5.shutdown()
        self._initialized = False
        self._clock_samples=[];self.clock_verified=False

    def ping(self) -> ConnectionStatus:
        if self._mt5 is None or not self._initialized:
            return ConnectionStatus(False, {"adapter": "mt5"}, self._import_error or "not initialized")
        ti = self._mt5.terminal_info()
        if ti is None:
            self._initialized = False
            return ConnectionStatus(False, {"adapter": "mt5"}, f"terminal_info failed: {self._err()}")
        detail = {"adapter": "mt5", "terminal_connected": bool(ti.connected),
                  "terminal_trade_allowed": bool(ti.trade_allowed),
                  "timestamp_clock_verified": self.clock_verified, "observed_server_utc_offset_seconds": self._utc_offset_seconds,
                  "company": getattr(ti, "company", None), "name": getattr(ti, "name", None)}
        if not ti.connected:
            return ConnectionStatus(False, detail, "terminal not connected to broker server")
        return ConnectionStatus(True, detail, None)

    # ---- account / positions ------------------------------------------------
    def account_info(self) -> Optional[AccountInfo]:
        a = self._mt5.account_info() if self._initialized else None
        if a is None:
            return None
        return AccountInfo(login=str(a.login), server=str(a.server),
                           is_demo=(a.trade_mode == ACCOUNT_TRADE_MODE_DEMO),
                           currency=str(a.currency), balance=float(a.balance), equity=float(a.equity),
                           margin=float(a.margin), free_margin=float(a.margin_free),
                           leverage=int(a.leverage), trade_allowed=bool(a.trade_allowed))

    def positions(self) -> Optional[list[BrokerPosition]]:
        if not self._initialized:
            return None
        ps = self._mt5.positions_get()
        if ps is None:
            return None
        return [BrokerPosition(
            ticket=str(p.ticket), symbol=p.symbol, side="buy" if p.type == 0 else "sell",
            volume=float(p.volume), price_open=float(p.price_open), price_current=float(p.price_current),
            sl=float(p.sl) or None, tp=float(p.tp) or None, profit=float(p.profit),
            magic=int(p.magic), comment=p.comment or None, time=None) for p in ps]

    def pending_orders(self) -> Optional[list[BrokerOrder]]:
        if not self._initialized:
            return None
        os_ = self._mt5.orders_get()
        if os_ is None:
            return None
        return [BrokerOrder(ticket=str(o.ticket), symbol=o.symbol, type=str(o.type),
                            volume=float(o.volume_current), price=float(o.price_open),
                            sl=float(o.sl) or None, tp=float(o.tp) or None, comment=o.comment or None)
                for o in os_]

    def quote(self, symbol: str) -> Optional[Quote]:
        if not self._initialized:
            return None
        t = self._mt5.symbol_info_tick(symbol)
        if t is None:
            self._mt5.symbol_select(symbol, True)
            return None
        now = self._clock()
        prev = self._tick_seen.get(symbol)
        raw = int(t.time_msc)/1000
        delta = raw-now.timestamp()
        candidate = round(delta/900)*900
        changed = prev is not None and prev[0] != int(t.time_msc)
        advancing = prev is not None and int(t.time_msc)>prev[0] and (now-prev[1]).total_seconds()>0
        cadence_ok = advancing and abs((int(t.time_msc)-prev[0])/1000-(now-prev[1]).total_seconds())<=5
        if cadence_ok and abs(candidate)<=14*3600 and abs(delta-candidate)<=5:
            self._clock_samples.append((symbol,candidate,now))
            self._clock_samples=[x for x in self._clock_samples[-100:] if (now-x[2]).total_seconds()<=30]
            matching=[x for x in self._clock_samples if x[1]==candidate]
            if len(matching)>=3 and len({x[0] for x in matching})>=2:
                self._utc_offset_seconds=candidate
                self.clock_verified=True
        if prev is None or prev[0]!=int(t.time_msc):
            self._tick_seen[symbol]=(int(t.time_msc),now)
        offset=self._utc_offset_seconds or 0
        return Quote(symbol=symbol,bid=float(t.bid),ask=float(t.ask),
                     time=datetime.fromtimestamp(raw-offset,timezone.utc))

    def contract_spec(self, symbol: str) -> Optional[ContractSpec]:
        if not self._initialized:
            return None
        si = self._mt5.symbol_info(symbol)
        if si is None:
            return None
        if not si.visible:
            self._mt5.symbol_select(symbol, True)
        return ContractSpec(symbol=symbol, tick_size=float(si.trade_tick_size),
                            tick_value_per_lot=float(si.trade_tick_value), point=float(si.point),
                            volume_min=float(si.volume_min), volume_max=float(si.volume_max),
                            volume_step=float(si.volume_step), min_stop_points=float(si.trade_stops_level))

    def margin_required(self, symbol: str, side: str, volume: float, price: float) -> Optional[float]:
        if not self._initialized:
            return None
        otype = self._mt5.ORDER_TYPE_BUY if side == "buy" else self._mt5.ORDER_TYPE_SELL
        m = self._mt5.order_calc_margin(otype, symbol, volume, price)
        return None if m is None else float(m)

    def historical_deals(self, since: datetime) -> Optional[list[dict]]:
        if not self._initialized or since.tzinfo is None:
            return None
        if not self.clock_verified:
            return None
        offset=self._utc_offset_seconds or 0
        deals = self._mt5.history_deals_get(since.astimezone(timezone.utc)+timedelta(seconds=offset), self._clock()+timedelta(seconds=offset+1))
        if deals is None:
            return None
        result=[]
        for deal in deals:
            row=dict(deal._asdict());row['raw_broker_time']=row.get('time');row['raw_broker_time_msc']=row.get('time_msc')
            # Current offset cannot prove historical DST. Retain an explicit uncertainty flag.
            row['time']=int(row['time'])-offset
            if 'time_msc' in row:row['time_msc']=int(row['time_msc'])-offset*1000
            row['timestamp_verification']='current_offset_only_historical_dst_unverified'
            result.append(row)
        return result

    def realized_pnl_since(self, since: datetime) -> Optional[float]:
        deals = self.historical_deals(since)
        if deals is None:
            return None
        return sum(float(d.get("profit",0)) + float(d.get("commission",0)) +
                   float(d.get("swap",0)) + float(d.get("fee",0))
                   for d in deals if int(d.get("type",-1)) in (0,1))

    def completed_bars(self, symbol: str, timeframe_seconds: int, count: int = 512) -> Optional[list[dict]]:
        if not self._initialized:
            return None
        names = {60:"M1",300:"M5",900:"M15",3600:"H1",14400:"H4",86400:"D1"}
        if timeframe_seconds not in names:
            return None
        rows = self._mt5.copy_rates_from_pos(symbol,getattr(self._mt5,"TIMEFRAME_"+names[timeframe_seconds]),1,count)
        if rows is None:
            return None
        if not self.clock_verified:
            return None
        now = self._clock().timestamp()
        offset=self._utc_offset_seconds or 0
        return [{**{k:row[k].item() for k in rows.dtype.names},"time":int(row["time"])-offset,
                 "raw_broker_time":int(row["time"]),"timestamp_verification":"current_live_calibration"}
                for row in rows if int(row["time"])-offset+timeframe_seconds<=now]

    # ---- orders -----------------------------------------------------------------
    def find_client_order(self, client_order_id: str) -> Optional[str]:
        if not self.clock_verified:
            raise RuntimeError("broker clock is not calibrated")
        tag = client_tag(client_order_id)
        positions=self._mt5.positions_get()
        orders=self._mt5.orders_get()
        now=self._clock()
        offset=self._utc_offset_seconds or 0
        deals=self._mt5.history_deals_get(now-timedelta(days=7)+timedelta(seconds=offset),now+timedelta(seconds=offset+1))
        if positions is None or orders is None or deals is None:
            raise RuntimeError("duplicate lookup incomplete; broker query failed")
        for p in positions:
            if (p.comment or "") == tag:
                return str(p.ticket)
        for o in orders:
            if (o.comment or "") == tag:
                return str(o.ticket)
        for d in deals:
            if (d.comment or "") == tag:
                return str(getattr(d, "position_id", d.ticket))
        return None

    def _filling(self, symbol: str) -> int:
        si = self._mt5.symbol_info(symbol)
        fm = int(getattr(si, "filling_mode", 0)) if si else 0
        if fm & 1:
            return self._mt5.ORDER_FILLING_FOK
        if fm & 2:
            return self._mt5.ORDER_FILLING_IOC
        return self._mt5.ORDER_FILLING_RETURN

    def send_market_order(self, req: OrderRequest) -> OrderResult:
        if not self.allow_orders:
            return OrderResult(False,message="host order execution disabled")
        if not self._initialized or not self.ping().connected:
            return OrderResult(False, message="not connected")
        if req.side not in ("buy","sell") or req.sl is None or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (req.volume,req.sl,req.tp or 0)) or req.volume<=0:
            return OrderResult(False,message="invalid order side, volume or prices")
        if req.sl is None or req.sl <= 0:
            return OrderResult(False, message="protective stop required")
        try:
            existing = self.find_client_order(req.client_order_id)
        except RuntimeError as exc:
            return OrderResult(False,message=str(exc),details={"outcome":"not_submitted"})
        if existing:
            return OrderResult(False, ticket=existing, duplicate=True,
                               message="duplicate client_order_id; order already exists at broker")
        tick = self._mt5.symbol_info_tick(req.symbol)
        if tick is None:
            return OrderResult(False, message="no tick")
        observed=self.quote(req.symbol)
        if observed is None or not self.clock_verified or not 0 <= (self._clock()-observed.time).total_seconds() <= 10 or not 0 < observed.bid <= observed.ask:
            return OrderResult(False,message="quote stale, invalid or broker clock unverified",details={"outcome":"not_submitted"})
        is_buy = req.side == "buy"
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL, "symbol": req.symbol, "volume": float(req.volume),
            "type": self._mt5.ORDER_TYPE_BUY if is_buy else self._mt5.ORDER_TYPE_SELL,
            "price": float(tick.ask if is_buy else tick.bid), "sl": float(req.sl),
            "tp": float(req.tp or 0.0), "deviation": int(req.deviation_points), "magic": int(req.magic),
            "comment": client_tag(req.client_order_id), "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(req.symbol),
        }
        # order_check does not execute. A successful check is necessary, not proof of a fill.
        checked = self._mt5.order_check(request)
        if checked is None or getattr(checked,"retcode",None) != 0:
            return OrderResult(False,message="broker preflight rejected: "+str(getattr(checked,"comment","query failed")),details={"outcome":"not_submitted"})
        if (is_buy and req.sl>=request["price"]) or (not is_buy and req.sl<=request["price"]):
            return OrderResult(False,message="protective stop on wrong side",details={"outcome":"not_submitted"})
        identity=self._mt5.account_info()
        if identity is None or (str(identity.server),str(identity.login))!=self._expected_identity:
            return OrderResult(False,message="broker account changed after connection",details={"outcome":"not_submitted"})
        res = self._mt5.order_send(request)
        if res is not None and res.retcode not in OK_RETCODES:
            return OrderResult(False, retcode=res.retcode, message=f"rejected: {res.comment}")
        # A pending order or deal proves receipt, not a protected open fill.
        # Verify the actual position, its filled volume, and broker-side stop.
        for _ in range(self._verify_attempts):
            positions = self._mt5.positions_get()
            pos = next((p for p in (positions or ())
                        if (p.comment or "") == client_tag(req.client_order_id)
                        and float(p.volume) > 0 and float(p.volume) <= req.volume + 1e-8
                        and float(p.sl) > 0 and getattr(p,"symbol",req.symbol)==req.symbol
                        and getattr(p,"type",0 if req.side=="buy" else 1)==(0 if req.side=="buy" else 1)
                        and ((req.side=="buy" and float(p.sl)>=req.sl-1e-9) or (req.side=="sell" and float(p.sl)<=req.sl+1e-9))), None)
            if pos is not None:
                return OrderResult(True, ticket=str(pos.ticket), retcode=getattr(res, "retcode", None),
                                   verified=True, fill_price=float(pos.price_open),
                                   filled_volume=float(pos.volume), message="filled and verified",
                                   details={"broker_sl": float(pos.sl), "partial_fill": float(pos.volume)<req.volume-1e-8})
            _time.sleep(self._verify_sleep)
        if res is None:
            return OrderResult(False, message=f"order_send returned None ({self._err()}); outcome unknown; reconcile")
        return OrderResult(False, ticket=str(res.order), retcode=res.retcode, verified=False,
                           message="broker reported success but position not observed; reconcile")

    def cancel_order(self, ticket: str) -> OrderResult:
        if not self._initialized:
            return OrderResult(False, ticket=ticket, message="not connected")
        res = self._mt5.order_send({"action": self._mt5.TRADE_ACTION_REMOVE, "order": int(ticket)})
        if res is None or res.retcode not in OK_RETCODES:
            return OrderResult(False, ticket=ticket, retcode=getattr(res, "retcode", None),
                               message=f"cancel failed: {getattr(res, 'comment', self._err())}")
        orders = self._mt5.orders_get()
        if orders is None:
            return OrderResult(False, ticket=ticket, message="cancel outcome unknown: order query failed")
        still = any(str(o.ticket) == ticket for o in orders)
        return OrderResult(not still, ticket=ticket, retcode=res.retcode, verified=not still,
                           message="cancelled" if not still else "cancel reported but order still present")

    def close_position(self, ticket: str) -> OrderResult:
        if not self._initialized:
            return OrderResult(False, ticket=ticket, message="not connected")
        positions = self._mt5.positions_get(ticket=int(ticket))
        if positions is None:
            return OrderResult(False, ticket=ticket, message="position query failed; outcome unknown")
        pos = next(iter(positions), None)
        if pos is None:
            return OrderResult(True, ticket=ticket, verified=True, message="position not open (already closed)")
        tick = self._mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return OrderResult(False, ticket=ticket, message="no tick for close")
        is_buy = pos.type == 0
        req = {"action": self._mt5.TRADE_ACTION_DEAL, "symbol": pos.symbol, "volume": float(pos.volume),
               "type": self._mt5.ORDER_TYPE_SELL if is_buy else self._mt5.ORDER_TYPE_BUY,
               "position": int(ticket), "price": float(tick.bid if is_buy else tick.ask),
               "deviation": 50, "magic": int(pos.magic), "comment": "QROS close",
               "type_time": self._mt5.ORDER_TIME_GTC, "type_filling": self._filling(pos.symbol)}
        res = self._mt5.order_send(req)
        if res is None or res.retcode not in OK_RETCODES:
            return OrderResult(False, ticket=ticket, retcode=getattr(res, "retcode", None),
                               message=f"close failed: {getattr(res, 'comment', self._err())}")
        positions = self._mt5.positions_get(ticket=int(ticket))
        if positions is None:
            return OrderResult(False, ticket=ticket, message="close outcome unknown: position query failed")
        still = next(iter(positions), None)
        return OrderResult(still is None, ticket=ticket, retcode=res.retcode, verified=still is None,
                           fill_price=float(res.price),
                           message="closed" if still is None else "close reported but position still open")
