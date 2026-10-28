"""Idempotent broker deal ingestion and managed-position journal reconciliation."""
from datetime import datetime,timezone,timedelta
import math
from sqlalchemy import select
from qros.audit.log import record
from qros.broker.base import client_tag
from qros.db.models import BrokerDeal,OrderLedger,Trade,ControlState,SystemState
from qros.services.execution import account_key,set_state,bind_broker_ticket,raw_trade_ticket,TicketBindingError
from qros.services import settings_store as st

def reconcile(db,adapter,now,mode):
    def unavailable(reason):
        set_state(db,'reconciliation',{'available':False,'clean':False,'reason':reason},now)
        ctrl=db.get(ControlState,1)
        if ctrl and ctrl.run_state=='running':
            ctrl.run_state='paused_entries';ctrl.halt_reason=reason;ctrl.updated_at=now
    acct=adapter.account_info();positions=adapter.positions();orders=adapter.pending_orders()
    if acct is None or positions is None or orders is None:
        unavailable('BROKER_QUERY_FAILED');return
    key=account_key(acct,mode)
    ledger=list(db.execute(select(OrderLedger).where(OrderLedger.account_key==key)).scalars())
    legacy_issues=[]
    # Do not silently bless unscoped pre-ledger journals using the active account.
    # Rows in other modes cannot be attributed here and remain untouched.
    for old in db.execute(select(Trade).where(Trade.mode==mode)).scalars():
        old_ledger=db.get(OrderLedger,old.client_order_id)
        if old_ledger is not None and old_ledger.account_key!=key:continue
        old_binding=db.get(SystemState,'trade_ticket_binding:'+str(old.broker_ticket))
        if old_binding is not None and old_binding.data.get('account_key')!=key:continue
        try:raw_trade_ticket(db,old,key,mode,now=now)
        except TicketBindingError as exc:
            # A valid scoped journal belonging to another account is isolated;
            # an unscoped ambiguous journal in this mode requires owner binding.
            legacy_issues.append(str(exc)+':'+old.client_order_id)
    earliest=min((st.as_utc(r.created_at) for r in ledger),default=now-timedelta(days=7))
    # A checkpoint overlaps query windows; deal IDs make overlap idempotent.
    checkpoint=db.get(SystemState,'reconcile_checkpoint:'+key)
    since=max(earliest-timedelta(days=1),datetime.fromisoformat(checkpoint.data['since'])-timedelta(days=1)) if checkpoint else earliest-timedelta(days=1)
    if getattr(adapter,'clock_verified',True) is False:
        # Distinguish a transient/closed-market calibration gap from a failed broker query.
        from qros.risk.calendar import is_weekend_market_closed
        unavailable('BROKER_CLOCK_NOT_VERIFIED_MARKET_CLOSED' if is_weekend_market_closed(now) else 'BROKER_CLOCK_NOT_YET_VERIFIED')
        return
    deals=adapter.historical_deals(since)
    if deals is None:
        unavailable('DEAL_HISTORY_QUERY_FAILED');return
    malformed=[]
    for deal in deals:
        if int(deal.get('type',-1)) not in (0,1):continue
        if any(not isinstance(deal.get(k,0),(int,float)) or not math.isfinite(deal.get(k,0)) for k in ('volume','price','profit','commission','fee','swap','time')):
            malformed.append('NONFINITE_BROKER_DEAL');continue
        did=str(deal.get('ticket',''))
        if not did:continue
        deal_key=key+':'+did
        if db.get(BrokerDeal,deal_key) is None:
            db.add(BrokerDeal(key=deal_key,account_key=key,position_id=str(deal.get('position_id','')),data=deal,observed_at=now))
    db.flush()
    all_deals=list(db.execute(select(BrokerDeal).where(BrokerDeal.account_key==key)).scalars())
    by_position={}
    for row in all_deals:by_position.setdefault(row.position_id,[]).append(row.data)
    issues=malformed+legacy_issues;managed_tickets=set()
    if orders:issues.append('PENDING_ORDERS_REQUIRE_REVIEW')
    def executions(items,entries):
        # Zero-volume normalized financing records retain cash accounting but
        # must never be mistaken for fills/entry volume or exit-price weights.
        return [d for d in items if int(d.get('entry',-1)) in entries and float(d.get('volume',0))>0 and float(d.get('price',0))>0]
    for intent in ledger:
        tag=client_tag(intent.client_order_id)
        tagged=[p for p in positions if p.comment==tag]
        trade=db.execute(select(Trade).where(Trade.client_order_id==intent.client_order_id)).scalar_one_or_none()
        if trade and trade.mode!=mode:
            issues.append('TRADE_ACCOUNT_OR_MODE_CONFLICT:'+intent.client_order_id);continue
        raw_ticket=None
        if trade:
            try:raw_ticket=raw_trade_ticket(db,trade,key,mode,ledger=intent,now=now)
            except TicketBindingError as exc:issues.append(str(exc)+':'+intent.client_order_id);continue
            managed_tickets.add(raw_ticket)
        for p in tagged:managed_tickets.add(str(p.ticket))
        # Find executions by comment OR known position ticket. Netting conflicts block entries.
        related=[d for row in by_position.values() for d in row if d.get('comment')==tag]
        position_ids={str(d.get('position_id','')) for d in executions(related,(0,))}
        if len(position_ids)==1:
            # Broker close comments commonly become [sl]/[tp]/manual. The
            # entry's position identifier binds the entire closed round trip.
            related=by_position.get(next(iter(position_ids)),related)
        elif len(position_ids)>1:
            issues.append('MULTIPLE_POSITIONS_FOR_INTENT:'+intent.client_order_id);continue
        if trade:related=by_position.get(raw_ticket,related)
        if any(d.get('comment')!=tag for d in executions(related,(0,))):
            # A netting position may combine QROS with manual/other-strategy
            # entries. Its aggregate PnL cannot be assigned to this intent.
            issues.append('MIXED_ENTRY_OWNERSHIP_REQUIRES_REVIEW:'+intent.client_order_id);continue
        if intent.status in ('submitting','unknown') and tagged:
            if len(tagged)!=1:
                issues.append('MULTIPLE_POSITIONS_FOR_INTENT:'+intent.client_order_id);continue
            p=tagged[0]
            expected=intent.request
            if p.symbol!=intent.symbol or p.side!=expected.get('side'):
                issues.append('POSITION_IDENTITY_MISMATCH:'+str(p.ticket));continue
            if not p.sl or not math.isfinite(p.sl) or p.sl<=0:issues.append('UNPROTECTED_MANAGED_POSITION:'+str(p.ticket));continue
            requested_stop=expected.get('stop_price')
            if requested_stop is None or (p.side=='buy' and p.sl<requested_stop-1e-9) or (p.side=='sell' and p.sl>requested_stop+1e-9):
                issues.append('PROTECTIVE_STOP_LOOSENED:'+str(p.ticket));continue
            if abs(p.volume-float(expected.get('volume',0)))>1e-8:issues.append('PARTIAL_OR_MANUAL_VOLUME_CHANGE:'+str(p.ticket))
            if trade is None:
                try:scoped_ticket=bind_broker_ticket(db,key,mode,str(p.ticket),intent.client_order_id,now)
                except TicketBindingError as exc:issues.append(str(exc)+':'+intent.client_order_id);continue
                trade=Trade(mode=mode,strategy_id=intent.strategy_id,symbol=p.symbol,side=p.side,volume=p.volume,entry_time=p.time or now,entry_price=p.price_open,intended_entry=intent.request['entry_price'],sl=p.sl,tp=p.tp,reason='Recovered verified broker position after uncertain submission',broker_ticket=scoped_ticket,client_order_id=intent.client_order_id)
                db.add(trade);managed_tickets.add(str(p.ticket))
            raw_ticket=str(p.ticket)
            intent.status='verified';intent.result={**intent.result,'ticket':raw_ticket,'verified_by_reconciliation':True,'filled_volume':p.volume};intent.updated_at=now
            record(db,'executor','order.reconciled',{'client_order_id':intent.client_order_id,'ticket':str(p.ticket)})
        if intent.status in ('submitting','unknown') and not tagged:
            # Receipt/deal history alone cannot authorize a resend. Record fully closed round trip only if volume proves it.
            entries=executions(related,(0,))
            exits=executions(related,(1,3))
            if entries and exits and sum(float(d.get('volume',0)) for d in exits)>=sum(float(d.get('volume',0)) for d in entries)-1e-8:
                e=entries[0];position=str(e.get('position_id',''));managed_tickets.add(position)
                if any(d.get('symbol')!=intent.symbol for d in entries) or any(int(d.get('type',-1))!=(0 if intent.request['side']=='buy' else 1) for d in entries):
                    issues.append('DEAL_IDENTITY_MISMATCH:'+intent.client_order_id);continue
                if abs(sum(float(d['volume']) for d in entries)-float(intent.request['volume']))>1e-8:issues.append('PARTIAL_OR_MANUAL_VOLUME_CHANGE:'+position)
                if trade is None:
                    try:scoped_ticket=bind_broker_ticket(db,key,mode,position,intent.client_order_id,now)
                    except TicketBindingError as exc:issues.append(str(exc)+':'+intent.client_order_id);continue
                    trade=Trade(mode=mode,strategy_id=intent.strategy_id,symbol=e['symbol'],side=intent.request['side'],volume=sum(float(d['volume']) for d in entries),entry_time=datetime.fromtimestamp(e['time'],timezone.utc),entry_price=sum(float(d['price'])*float(d['volume']) for d in entries)/sum(float(d['volume']) for d in entries),sl=intent.request['stop_price'],tp=intent.request.get('take_profit'),reason='Recovered broker-confirmed closed round trip',broker_ticket=scoped_ticket,client_order_id=intent.client_order_id)
                    db.add(trade)
                raw_ticket=position
                intent.result={**intent.result,'ticket':raw_ticket,'verified_by_reconciliation':True}
                intent.status='verified'
            else:issues.append('UNRESOLVED_ORDER:'+intent.client_order_id)
        if trade is None:continue
        current=next((p for p in positions if str(p.ticket)==raw_ticket),None)
        if current:
            if not current.sl or not math.isfinite(current.sl) or current.sl<=0:issues.append('UNPROTECTED_MANAGED_POSITION:'+str(current.ticket))
            if current.symbol!=trade.symbol or current.side!=trade.side:issues.append('POSITION_IDENTITY_MISMATCH:'+str(current.ticket))
            if abs(current.volume-trade.volume)>1e-8:issues.append('PARTIAL_OR_MANUAL_VOLUME_CHANGE:'+str(current.ticket))
            if trade.sl and current.sl and ((current.side=='buy' and current.sl<trade.sl-1e-9) or (current.side=='sell' and current.sl>trade.sl+1e-9)):
                issues.append('PROTECTIVE_STOP_LOOSENED:'+str(current.ticket))
        related=by_position.get(raw_ticket,related)
        exits=executions(related,(1,3))
        entries=executions(related,(0,))
        if any(int(d.get('entry',-1))==2 for d in related):issues.append('NETTING_REVERSAL_REQUIRES_REVIEW:'+raw_ticket)
        if current is None and trade.exit_time is None:
            exit_volume=sum(float(d.get('volume',0)) for d in exits)
            entry_volume=sum(float(d.get('volume',0)) for d in entries)
            if exits and entries and exit_volume>=entry_volume-1e-8:
                trade.exit_time=datetime.fromtimestamp(max(int(d['time']) for d in exits),timezone.utc)
                trade.exit_price=sum(float(d['price'])*float(d['volume']) for d in exits)/exit_volume
                trade.commission=sum(float(d.get('commission',0))+float(d.get('fee',0)) for d in related)
                trade.swap=sum(float(d.get('swap',0)) for d in related)
                trade.pnl=sum(float(d.get('profit',0)) for d in related)+trade.commission+trade.swap
                trade.exit_reason='broker_deal_reconciliation';intent.status='closed';intent.updated_at=now
                record(db,'executor','trade.closed',{'client_order_id':intent.client_order_id,'pnl':trade.pnl})
            else:issues.append('MISSING_POSITION_WITHOUT_COMPLETE_DEALS:'+raw_ticket)
    external=[str(p.ticket) for p in positions if str(p.ticket) not in managed_tickets]
    if external:issues.append('EXTERNAL_POSITIONS_REQUIRE_REVIEW')
    clean=not issues
    set_state(db,'reconciliation',{'available':True,'clean':clean,'account_key':key,'issues':sorted(set(issues)),'external_positions':external,'position_count':len(positions),'pending_orders':len(orders),'observed_at':now.isoformat()},now)
    set_state(db,'reconcile_checkpoint:'+key,{'since':now.isoformat()},now)
    ctrl=db.get(ControlState,1)
    if issues and ctrl and ctrl.run_state=='running':
        ctrl.run_state='paused_entries';ctrl.halt_reason='RECONCILIATION_REVIEW_REQUIRED';ctrl.updated_at=now
        record(db,'executor','reconciliation.paused',{'issues':sorted(set(issues))})
