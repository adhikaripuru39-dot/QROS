"""Single entry pipeline: observation -> independent gate -> durable intent -> broker.
An ambiguous broker outcome is recorded, pauses entries, and is NEVER auto-retried.
"""
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,math
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from qros.audit.log import record
from qros.broker.base import OrderRequest,OrderResult
from qros.config.schemas import TradingMode,RunState
from qros.db.models import OrderLedger,ControlState,RiskStateRow,Strategy,Trade,SystemState
from qros.db.session import session_scope
from qros.risk.calendar import in_trading_hours,last_reset,minutes_to_weekend_close,is_weekend_market_closed
from qros.risk.drawdown import AccountState
from qros.risk.gate import GateContext,InstrumentState,OpenPosition,check_order
from qros.risk.sizing import loss_per_lot
from qros.risk.news import configured_news
from qros.services import settings_store as st

def account_key(account,mode):
    return hashlib.sha256(f'{mode}|{account.server}|{account.login}'.encode()).hexdigest()


class TicketBindingError(ValueError):
    """A journal ticket cannot safely be assigned to the observed account."""


def scoped_ticket_key(key,raw_ticket):
    """32-character scope digest fits existing VARCHAR(32), including PostgreSQL.

    SystemState holds the complete account/mode/raw-ticket binding, checked on every
    lookup so a truncated digest collision cannot silently alias another trade.
    """
    if not key or raw_ticket is None or not str(raw_ticket):
        raise TicketBindingError('MISSING_TICKET_BINDING')
    return 'q:'+hashlib.sha256((key+'|'+str(raw_ticket)).encode()).hexdigest()[:30]


def bind_broker_ticket(db,key,mode,raw_ticket,client_order_id,now):
    mode=getattr(mode,'value',mode);raw=str(raw_ticket)
    scoped=scoped_ticket_key(key,raw)
    data={'account_key':key,'mode':mode,'raw_ticket':raw,'client_order_id':client_order_id}
    state=db.get(SystemState,'trade_ticket_binding:'+scoped)
    if state and state.data!=data:
        raise TicketBindingError('POSITION_TICKET_ALREADY_BOUND_REQUIRES_REVIEW')
    existing=db.execute(select(Trade).where(Trade.broker_ticket==scoped)).scalar_one_or_none()
    if existing is not None and existing.client_order_id!=client_order_id:
        raise TicketBindingError('POSITION_TICKET_ALREADY_JOURNALED_REQUIRES_REVIEW')
    if state is None:set_state(db,'trade_ticket_binding:'+scoped,data,now)
    return scoped


def raw_trade_ticket(db,trade,key,mode,*,ledger=None,explicit_binding=None,now=None):
    """Resolve exact raw IDs. Legacy rows require a durable or explicit binding.

    An old unscoped ID is never attributed from its numeric shape, the currently
    connected account, or a matching external position alone.
    """
    mode=getattr(mode,'value',mode)
    if trade.mode!=mode or not trade.broker_ticket:
        raise TicketBindingError('TRADE_ACCOUNT_OR_MODE_CONFLICT')
    stored=str(trade.broker_ticket)
    if stored.startswith('q:'):
        state=db.get(SystemState,'trade_ticket_binding:'+stored)
        if state is None or state.data.get('account_key')!=key or state.data.get('mode')!=mode or state.data.get('client_order_id')!=trade.client_order_id:
            raise TicketBindingError('MISSING_OR_CONFLICTING_SCOPED_TICKET_BINDING')
        raw=state.data.get('raw_ticket')
        if scoped_ticket_key(key,raw)!=stored:
            raise TicketBindingError('SCOPED_TICKET_DIGEST_MISMATCH')
        return str(raw)
    ledger=ledger or db.get(OrderLedger,trade.client_order_id)
    durable=(ledger is not None and ledger.account_key==key and ledger.mode==mode and ledger.client_order_id==trade.client_order_id)
    explicit=(isinstance(explicit_binding,dict) and explicit_binding.get('account_key')==key and
              explicit_binding.get('mode')==mode and str(explicit_binding.get('raw_ticket'))==stored and
              explicit_binding.get('client_order_id')==trade.client_order_id and bool(explicit_binding.get('source')))
    if not durable and not explicit:
        raise TicketBindingError('AMBIGUOUS_LEGACY_TRADE_REQUIRES_ACCOUNT_BINDING')
    trade.broker_ticket=bind_broker_ticket(db,key,mode,stored,trade.client_order_id,now or datetime.now(timezone.utc))
    record(db,'executor','trade.ticket_scoped',{'client_order_id':trade.client_order_id,'account_key':key,
        'mode':mode,'raw_ticket':stored,'binding_source':'durable_order_ledger' if durable else explicit_binding['source']})
    return stored

def set_state(db,key,data,now):
    row=db.get(SystemState,key)
    if row is None:db.add(SystemState(key=key,data=data,updated_at=now))
    else:row.data=data;row.updated_at=now

def execute_intent(factory,adapter,settings,intent,client_order_id,now=None):
    now=now or datetime.now(timezone.utc)
    with session_scope(factory) as db:
        existing=db.get(OrderLedger,client_order_id)
        if existing:return {'status':'duplicate','ledger_status':existing.status,'client_order_id':client_order_id}
        ctrl=db.get(ControlState,1);firm=st.active_firm(db);limits=st.internal_limits(db)
        mode=TradingMode(ctrl.trading_mode);extra=[]
        if mode!=TradingMode.PAPER and not settings.order_execution_enabled:extra.append('HOST_ORDER_EXECUTION_DISABLED')
        if mode in (TradingMode.DEMO,TradingMode.LIVE) and firm.is_example:extra.append('EXAMPLE_FIRM_PROFILE')
        strategy=db.get(Strategy,intent.strategy_id)
        if strategy is None or strategy.status!=intent.strategy_status:extra.append('STRATEGY_NOT_REGISTERED_OR_STATUS_CHANGED')
        if intent.strategy_id not in (ctrl.active_strategy_ids or []):extra.append('STRATEGY_NOT_ACTIVE')
        if strategy is not None:
            from qros.services.evidence import strategy_eligibility
            extra.extend(strategy_eligibility(db,strategy,mode.value))
        unknown=db.execute(select(OrderLedger).where(OrderLedger.status.in_(['submitting','unknown']))).scalars().first()
        if unknown:extra.append('UNRESOLVED_ORDER_OUTCOME')
        acct=adapter.account_info();positions=adapter.positions();quote=adapter.quote(intent.symbol);spec=adapter.contract_spec(intent.symbol)
        if acct is None or positions is None or quote is None or spec is None:
            return {'status':'rejected','reasons':extra+['BROKER_OBSERVATION_INCOMPLETE']}
        from qros.services.account_rules import account_rule_errors
        extra.extend(account_rule_errors(db,firm,acct.server,acct.login))
        if strategy is not None and strategy.status=='DEMO_TESTING':
            from qros.services.demo_testing import grant_errors
            extra.extend(grant_errors(db,strategy,mode.value,now,acct,settings))
        if acct.currency!=firm.currency:extra.append('ACCOUNT_CURRENCY_MISMATCH')
        if not acct.trade_allowed and mode!=TradingMode.PAPER:extra.append('BROKER_TRADING_NOT_ALLOWED')
        if mode==TradingMode.DEMO and acct.is_demo is not True:extra.append('DEMO_REQUIRES_DEMO_ACCOUNT')
        if mode==TradingMode.LIVE and acct.is_demo is not False:extra.append('LIVE_REQUIRES_REAL_ACCOUNT')
        key=account_key(acct,mode.value)
        binding=db.get(SystemState,'execution_account_binding')
        if binding and binding.data.get('account_key')!=key:extra.append('EXECUTION_ACCOUNT_CHANGED_OWNER_REVIEW_REQUIRED')
        reconciled=db.get(SystemState,'reconciliation')
        if reconciled is None or not reconciled.data.get('available') or not reconciled.data.get('clean') or reconciled.data.get('account_key')!=key or not 0<=(now-st.as_utc(reconciled.updated_at)).total_seconds()<=settings.stale_after_seconds:
            extra.append('RECONCILIATION_MISSING_STALE_OR_UNCLEAN')
        rs=db.get(RiskStateRow,1)
        if rs is None or rs.firm_id!=firm.id or (now-st.as_utc(rs.computed_at)).total_seconds()>settings.stale_after_seconds:
            return {'status':'rejected','reasons':extra+['RISK_STATE_STALE_OR_MISSING']}
        d=rs.data
        if mode in (TradingMode.DEMO,TradingMode.LIVE) and d.get("anchor_method")!="observed_at_reset":extra.append("FIRM_RESET_ANCHOR_NOT_VERIFIED")
        account=AccountState(acct.balance,acct.equity,firm.initial_balance,d['sod_balance'],d['sod_equity'],rs.hwm_equity,rs.hwm_eod_balance)
        instruments={i.symbol:i for i in st.instruments(db)};ic=instruments.get(intent.symbol)
        if ic is None:return {'status':'rejected','reasons':['INSTRUMENT_NOT_CONFIGURED']}
        opened=[]
        for p in positions:
            cfg=instruments.get(p.symbol);contract=adapter.contract_spec(p.symbol)
            if cfg is None or contract is None:extra.append('UNRECOGNIZED_OPEN_POSITION:'+p.symbol);continue
            distance=(p.price_current-p.sl) if p.side=='buy' and p.sl else (p.sl-p.price_current) if p.sl else None
            risk=None if distance is None else max(0,distance)/contract.tick_size*contract.tick_value_per_lot*p.volume
            if risk is not None:risk+=limits.slippage_buffer_points*contract.point/contract.tick_size*contract.tick_value_per_lot*p.volume+firm.commission_per_lot_round_turn*p.volume
            opened.append(OpenPosition(p.symbol,cfg.base,cfg.quote,p.side,p.volume,risk))
        realized=adapter.realized_pnl_since(last_reset(now,firm.daily_reset))
        if realized is None:extra.append('REALIZED_SESSION_PNL_UNKNOWN')
        news_source=getattr(adapter,'source',adapter)
        news_connection=news_source.ping()
        news_account=news_source.account_info() if mode==TradingMode.PAPER else acct
        coverage,blackout,news_reason=configured_news(settings,firm,now,{ic.base,ic.quote},
            expected_server=news_account.server if news_account else None,
            expected_offset=news_connection.detail.get('observed_server_utc_offset_seconds'))
        if not coverage:extra.append('NEWS_CALENDAR_UNAVAILABLE_OR_STALE:'+news_reason)
        if settings.news_filter_enabled and blackout:extra.append('NEWS_BLACKOUT')
        hours=st.trading_hours(db)
        today=last_reset(now,firm.daily_reset)
        n=db.execute(select(func.count(OrderLedger.client_order_id)).where(OrderLedger.created_at>=today,OrderLedger.status.in_(['verified','closed','submitting','unknown']))).scalar() or 0
        context=GateContext(firm,limits,account,InstrumentState(spec,ic.base,ic.quote,ic.enabled,ic.max_spread_points,quote.bid,quote.ask,quote.time),opened,now,mode,RunState(ctrl.run_state),ctrl.kill_switch,adapter.ping().connected,settings.live_trading_enabled,n,realized or 0,in_trading_hours(now,hours),blackout,0 if is_weekend_market_closed(now) else minutes_to_weekend_close(now),hours.flat_before_weekend_minutes,acct.free_margin,adapter.margin_required(intent.symbol,intent.side,intent.volume,intent.entry_price))
        decision=check_order(intent,context)
        # Quote movement can change geometry/risk after a signal was calculated.
        actual_entry=quote.ask if intent.side=='buy' else quote.bid
        if abs(actual_entry-intent.entry_price)>limits.slippage_buffer_points*spec.point:extra.append('ENTRY_MOVED_REEVALUATE_SIGNAL')
        reasons=extra+decision.reasons
        row=OrderLedger(client_order_id=client_order_id,account_key=key,strategy_id=intent.strategy_id,symbol=intent.symbol,mode=mode.value,status='rejected' if reasons else 'submitting',request=asdict(intent),decision={**asdict(decision),'reasons':reasons,'approved':not reasons},result={})
        db.add(row)
        record(db,'executor','order.intent',{'client_order_id':client_order_id,'approved':not reasons,'reasons':reasons})
        if reasons:return {'status':'rejected','reasons':reasons}
        if binding is None:set_state(db,'execution_account_binding',{'account_key':key},now)
    # Transaction above is durable before any remote side effect.
    request=OrderRequest(client_order_id,intent.symbol,intent.side,intent.volume,intent.stop_price,intent.take_profit)
    try:
        current_account=adapter.account_info()
        if current_account is None or account_key(current_account,mode.value)!=key:
            result=OrderResult(False,message='Account changed after risk decision',details={'outcome':'not_submitted'})
        else:
            result=adapter.send_market_order(request)
    except Exception as exc:result=OrderResult(False,message=f'{type(exc).__name__}: {exc}',details={'outcome':'unknown'})
    with session_scope(factory) as db:
        row=db.get(OrderLedger,client_order_id)
        if (mode==TradingMode.PAPER and not result.ok and not result.ticket and not result.verified and
            not result.filled_volume and not result.fill_price and result.retcode is None and
            result.details.get('outcome') not in ('unknown','submitted','uncertain')):
            # An explicit paper rejection with no simulated-fill evidence has no
            # remote side effect. Exceptions/receipts/fills remain ambiguous.
            result=OrderResult(**{**asdict(result),'details':{**result.details,'outcome':'not_submitted'}})
        row.result=asdict(result);row.updated_at=now
        broker_stop=result.details.get('broker_sl')
        verified_fill=(result.ok and result.verified and result.ticket and all(isinstance(x,(float,int)) and math.isfinite(x) and x>0 for x in (result.filled_volume,result.fill_price,broker_stop))
            and result.filled_volume<=intent.volume+1e-8 and ((intent.side=='buy' and intent.stop_price<=broker_stop<result.fill_price) or (intent.side=='sell' and intent.stop_price>=broker_stop>result.fill_price)))
        if verified_fill:
            row.status='verified'
            if abs(result.filled_volume-intent.volume)>1e-8:
                row.result={**row.result,'partial_fill':True}
                ctrl=db.get(ControlState,1);ctrl.run_state='paused_entries';ctrl.halt_reason='PARTIAL_FILL_REQUIRES_REVIEW:'+client_order_id
            if db.execute(select(Trade).where(Trade.client_order_id==client_order_id)).scalar_one_or_none() is None:
                try:ticket=bind_broker_ticket(db,key,row.mode,result.ticket,client_order_id,now)
                except TicketBindingError as exc:
                    row.status='unknown';row.result={**row.result,'journal_binding_error':str(exc)}
                    ctrl=db.get(ControlState,1);ctrl.run_state='paused_entries';ctrl.halt_reason='POSITION_JOURNAL_BINDING_REQUIRES_REVIEW:'+client_order_id
                else:
                    db.add(Trade(mode=row.mode,strategy_id=intent.strategy_id,symbol=intent.symbol,side=intent.side,volume=result.filled_volume,entry_time=now,entry_price=result.fill_price,intended_entry=intent.entry_price,sl=result.details.get('broker_sl',intent.stop_price),tp=intent.take_profit,reason=('Unvalidated owner-authorized demo experiment' if intent.strategy_status=='DEMO_TESTING' else 'Validated completed-bar signal')+'; passed independent risk gate',broker_ticket=ticket,client_order_id=client_order_id,risk_amount=row.decision.get('metrics',{}).get('new_trade_risk')))
        elif result.details.get('outcome')=='not_submitted' or result.retcode in (10004,10006,10007,10013,10014,10015,10016,10017,10018,10019,10020,10021,10022,10024,10026,10027,10030,10032,10033,10034,10035,10038,10042,10043,10044,10045,10046):
            row.status='rejected'
        else:
            row.status='unknown'
            ctrl=db.get(ControlState,1);ctrl.run_state='paused_entries';ctrl.halt_reason='UNRESOLVED_ORDER_OUTCOME:'+client_order_id
        record(db,'executor','order.'+row.status,{'client_order_id':client_order_id,'result':row.result})
        return {'status':row.status,'client_order_id':client_order_id,'result':row.result}
