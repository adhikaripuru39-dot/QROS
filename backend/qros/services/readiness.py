"""Readiness is derived from observations/evidence, never from a UI mode label."""
from datetime import datetime,timezone
from sqlalchemy import select
from qros.db.models import ServiceHeartbeat,RiskStateRow,OrderLedger,Strategy,SystemState,EvidenceReport
from qros.services import settings_store as st
from qros.services.evidence import strategy_eligibility

def readiness(db,settings,now=None):
    now=now or datetime.now(timezone.utc);checks=[]
    def check(name,passed,detail):checks.append({'name':name,'passed':bool(passed),'detail':detail})
    hb=db.get(ServiceHeartbeat,'executor');firm=st.active_firm(db);risk=db.get(RiskStateRow,1)
    alive=bool(hb and (now-st.as_utc(hb.last_beat)).total_seconds()<=settings.stale_after_seconds)
    detail=hb.broker_detail if hb else {}
    check('executor_online',alive,'Fresh executor heartbeat required')
    check('broker_connected',alive and hb.broker_connected and detail.get('snapshot_ok'),'Complete account, positions, orders snapshot required')
    check('verified_firm_profile',not firm.is_example,'Free Trial selected; 1-Step/2-Step/Instant rules and initial capital must match account')
    if str(detail.get('server','')).upper().startswith('FTMO'):
        from qros.services.account_rules import account_rule_errors
        errors=account_rule_errors(db,firm,detail['server'],detail.get('login'))
        check('ftmo_account_rules_bound',not errors,errors or 'Programme rules match the reviewed account identity; funded Standard requires a separate rules review')
    check('risk_observation_current',risk and risk.firm_id==firm.id and 0 <= (now-st.as_utc(risk.computed_at)).total_seconds()<=settings.stale_after_seconds,'Risk anchors must be current for the connected account')
    check('risk_anchor_verified',risk and risk.data.get('anchor_method')=='observed_at_reset','A conservative first-observation estimate is not proof of the firm reset anchor')
    check('risk_within_limits',risk and not risk.data.get('halt_required'),'No active daily/total risk breach')
    check('terminal_algorithmic_permission',detail.get('terminal_trade_allowed',False),'MT5 Algo Trading must be enabled by owner before broker execution')
    check('host_execution_permission',settings.order_execution_enabled,'QROS_ORDER_EXECUTION_ENABLED must be explicitly enabled')
    check('broker_clock_verified',detail.get('timestamp_clock_verified',False),'Current clock calibration required; raw historical timestamps have separate verification')
    unresolved=db.execute(select(OrderLedger).where(OrderLedger.status.in_(['submitting','unknown']))).scalars().first()
    check('order_outcomes_resolved',unresolved is None,'Uncertain submissions block new entries and are never blindly retried')
    rec=db.get(SystemState,'reconciliation')
    check('reconciliation_clean',rec and rec.data.get('clean') and (now-st.as_utc(rec.updated_at)).total_seconds()<=settings.stale_after_seconds,'Broker deals, managed/external positions must reconcile')
    strategies=list(db.execute(select(Strategy)).scalars())
    eligible=[];demo_tests=[]
    evidence_mode='demo' if detail.get('is_demo') is True else 'live'
    for strategy in strategies:
        if strategy.status=='DEMO_TESTING' and evidence_mode=='demo':
            from qros.services.demo_testing import grant_errors
            if not grant_errors(db,strategy,'demo',now,settings=settings):demo_tests.append(strategy)
        if strategy.status not in ('DEMO_APPROVED','LIVE_APPROVED','ACTIVE'):continue
        try:
            if not strategy_eligibility(db,strategy,evidence_mode):eligible.append(strategy)
        except (ValueError,TypeError,KeyError,ArithmeticError):continue
    check('strategy_execution_permission',bool(eligible or demo_tests),'Validated strategy or expiring unvalidated DEMO_TESTING permission; demo experiments never qualify for live')
    if firm.news.enabled or settings.news_filter_enabled:
        from qros.risk.news import configured_news
        currencies={c for instrument in st.instruments(db) if instrument.enabled for c in (instrument.base,instrument.quote)}
        valid,_,reason=configured_news(settings,firm,now,currencies,
            expected_server=None if detail.get('paper') else detail.get('server'),expected_offset=detail.get('observed_server_utc_offset_seconds'))
        check('news_calendar_coverage',valid,reason)
    checks_by_name={c['name']:c['passed'] for c in checks}
    common=all(c['passed'] for c in checks)
    is_demo=detail.get('is_demo') is True
    live_strategies=[s for s in eligible if s.status in ('LIVE_APPROVED','ACTIVE')]
    blockers=[c['name'] for c in checks if not c['passed']]
    worker=db.get(ServiceHeartbeat,'research_worker')
    return {'observed_at':now.isoformat(),'checks':checks,'blockers':blockers,'ready_for_demo':common and is_demo,'ready_for_live':common and detail.get('is_demo') is False and settings.live_trading_enabled and bool(live_strategies),'demo_experiments':[s.id for s in demo_tests],'demo_experiments_validated':False,'ready_for_paper':alive and checks_by_name['broker_clock_verified'] and settings.paper_initial_balance is not None and settings.paper_commission_per_lot_round_turn is not None and settings.paper_swap_per_lot_day is not None,'account_is_demo':detail.get('is_demo'),'live_enabled_on_host':settings.live_trading_enabled,'research_worker_online':bool(worker and (now-st.as_utc(worker.last_beat)).total_seconds()<120),'reconciliation':rec.data if rec else None,'telegram':'deferred_until_final_phase','software_modules':['data','backtest','research','validation','signals','paper_broker','reconciliation','deployment'],'operational_approval':'pending' if blockers else 'eligible_for_owner_review'}
