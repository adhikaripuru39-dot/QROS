"""Weekly observations; closed-trade P&L is already net in the journal."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter
from sqlalchemy import select
from qros.db.models import Trade, OrderLedger, EvidenceReport, SystemState, SignalLog
from qros.reporting.stats import ClosedTrade, summarize
from qros.services.settings_store import as_utc
from qros.services.evidence import canonical_hash

def weekly_report(db, strategy, week, mode, tz='Asia/Katmandu', now=None):
    now = now or datetime.now(timezone.utc)
    if week.weekday() != 0: raise ValueError('Choose a Monday as the week start')
    zone = ZoneInfo(tz)
    start = datetime.combine(week, time(), zone).astimezone(timezone.utc)
    end = datetime.combine(week+timedelta(days=7), time(), zone).astimezone(timezone.utc)
    if start > now: raise ValueError('Future review weeks are unavailable')
    closed = list(db.execute(select(Trade).where(Trade.strategy_id==strategy.id,
        Trade.mode==mode,Trade.exit_time>=start,Trade.exit_time<end).order_by(Trade.exit_time,Trade.id)).scalars())
    open_trades = list(db.execute(select(Trade).where(Trade.strategy_id==strategy.id,
        Trade.mode==mode,Trade.entry_time<min(now,end))).scalars())
    open_at_cutoff = [t for t in open_trades if t.exit_time is None or as_utc(t.exit_time)>=min(now,end)]
    orders = list(db.execute(select(OrderLedger).where(OrderLedger.strategy_id==strategy.id,
        OrderLedger.mode==mode,OrderLedger.created_at>=start,OrderLedger.created_at<end)).scalars())
    signals = list(db.execute(select(SignalLog).where(SignalLog.strategy_id==strategy.id,
        SignalLog.mode==mode,SignalLog.created_at>=start,SignalLog.created_at<end)).scalars())
    reports = list(db.execute(select(EvidenceReport).where(EvidenceReport.strategy_id==strategy.id,
        EvidenceReport.created_at>=start,EvidenceReport.created_at<end).order_by(EvidenceReport.created_at)).scalars())
    valid = [t for t in closed if t.pnl is not None]
    r_values = [t.pnl/t.risk_amount for t in valid if t.risk_amount and t.risk_amount>0]
    payload = {'strategy_id':strategy.id,'strategy_name':strategy.name,'status':strategy.status,
        'runtime':strategy.spec.get('runtime',{}),'runtime_hash':canonical_hash(strategy.spec.get('runtime',{})),
        'week_start':week.isoformat(),'timezone':tz,'start_utc':start.isoformat(),'end_utc_exclusive':end.isoformat(),
        'mode':mode,'period_complete':end<=now,'open_at_cutoff':len(open_at_cutoff),
        'statistics':summarize(ClosedTrade(t.symbol,t.strategy_id,as_utc(t.exit_time),t.pnl,t.slippage_points) for t in valid),
        'net_pnl':sum(t.pnl for t in valid) if valid else None,
        'mean_r':sum(r_values)/len(r_values) if r_values else None,'r_sample_size':len(r_values),
        'commission':sum(t.commission for t in valid),'swap':sum(t.swap for t in valid),
        'missing_pnl_count':len(closed)-len(valid),'order_status_counts':dict(Counter(o.status for o in orders)),
        'signal_reason_counts':dict(Counter(s.reason for s in signals)),
        'research_reports':[{'id':r.id,'passed':r.passed,'report_hash':r.report_hash,
            'candidate_metrics':next((c for c in r.content.get('candidates',[]) if c.get('strategy_id')==strategy.hypothesis_id),None),
            'eligible':r.content.get('eligible',False),'oos_evaluated':r.content.get('oos',{}).get('evaluated',False)} for r in reports],
        'trades':[{'id':t.id,'symbol':t.symbol,'side':t.side,'exit_time':as_utc(t.exit_time).isoformat(),
            'net_pnl':t.pnl,'commission':t.commission,'swap':t.swap,'risk_amount':t.risk_amount,
            'exit_reason':t.exit_reason} for t in closed],
        'interpretation':'No forward evidence' if not valid else 'Weekly observations are not a profitability verdict',
        'review_checklist':['Check feed/cost integrity before interpreting P&L','Separate paper/demo/live and versions',
            'Review expectancy, drawdown, sample size and execution costs together',
            'Record one falsifiable change; preserve the previous version and final holdout']}
    payload['snapshot_hash']=canonical_hash(payload)
    return payload
