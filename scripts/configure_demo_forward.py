"""Owner commissioning for this reviewed Free Trial only. Never sends orders.

Creates expiring permissions, leaves strategy validation unchanged, and selects
demo strategies through the executor command API. Start is a separate command
after actual readiness passes. Re-running never renews an existing grant.
"""
import argparse
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from qros.config.settings import Settings
from qros.db.session import session_factory,session_scope
from qros.db.models import Strategy,SystemState,StrategyTransition,ControlState
from qros.services import settings_store as st
from qros.services.evidence import canonical_hash
from qros.services.execution import account_key
from qros.services.account_rules import identity,account_rule_errors
from qros.broker.base import AccountInfo
from qros.research.runner import implementation_hash
from qros.audit.log import record


def configure():
    parser=argparse.ArgumentParser()
    parser.add_argument('--configure',action='store_true',required=True)
    parser.add_argument('--rebind-unused-code',action='store_true',help='Review and rebind code only when no strategy order has ever been submitted; does not extend expiry')
    args=parser.parse_args()
    settings=Settings()
    # Explicit intended local trial. A different account requires a fresh review.
    import MetaTrader5 as mt5
    if not mt5.initialize(path=settings.mt5_path,timeout=15000):raise RuntimeError('MT5 connection failed')
    try:
        a=mt5.account_info();terminal=mt5.terminal_info()
        if a is None or a.server!='FTMO-Demo' or a.login!=1514976566 or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise ValueError('Only the reviewed local FTMO Free Trial is authorized')
        if not terminal or not terminal.connected:raise ValueError('Terminal disconnected')
        account=AccountInfo(str(a.login),a.server,True,a.currency,a.balance,a.equity,a.margin,a.margin_free,a.leverage,a.trade_allowed)
    finally:mt5.shutdown()
    now=datetime.now(timezone.utc);configured=[]
    with session_scope(session_factory(settings.database_url)) as db:
        ctrl=db.get(ControlState,1)
        if ctrl.run_state!='stopped' or ctrl.trading_mode not in ('off','demo'):raise ValueError('Stop executor before configuration')
        firm=st.active_firm(db)
        if firm.id!='ftmo_free_trial_50k_2step' or firm.initial_balance!=50000 or firm.is_example:
            raise ValueError('Reviewed $50k 2-Step Free Trial profile required')
        if account_rule_errors(db,firm,a.server,a.login):raise ValueError('Reviewed account binding required')
        limits=st.internal_limits(db).model_dump(mode='json')
        limits.update(risk_per_trade_pct=.05,daily_warning_pct=.25,daily_stop_pct=.5,
                      total_stop_pct=2.,max_open_positions=1,max_risk_per_instrument_pct=.1,
                      max_total_open_risk_pct=.1,max_currency_risk_pct=.1,
                      max_session_loss_pct=.5,max_trades_per_day=6)
        st.set_internal_limits(db,limits,'owner-demo-commissioning')
        for strategy in db.execute(select(Strategy).where(Strategy.id.like('lib_v1_%'))).scalars():
            key='demo_test_grant:'+strategy.id
            if db.get(SystemState,key) is not None:
                if args.rebind_unused_code:
                    from qros.db.models import OrderLedger
                    if db.execute(select(OrderLedger).where(OrderLedger.strategy_id==strategy.id)).first():
                        raise ValueError('Cannot rebind a strategy with broker intents; create a new version')
                    grant=db.get(SystemState,key)
                    previous=grant.data['code_hash']
                    grant.data={**grant.data,'code_hash':implementation_hash()};grant.updated_at=now
                    record(db,'owner-demo-commissioning','demo.grant.unused_code_reviewed',{
                        'strategy_id':strategy.id,'previous_code_hash':previous,'code_hash':implementation_hash(),
                        'expires_at_unchanged':grant.data['expires_at']})
                configured.append(strategy.id);continue
            if strategy.status!='IDEA':raise ValueError('Expected untouched IDEA baseline')
            grant={'actor_kind':'owner','source':'Owner requested direct MT5 demo forward testing on 2026-10-24',
                   'programme':'2-Step Free Trial','funded':False,'server':a.server,
                   'account_key':account_key(account,'demo'),'account_identity':identity(a.server,a.login),
                   'firm_id':firm.id,'authorized_at':now.isoformat(),'expires_at':(now+timedelta(days=7)).isoformat(),
                   'strategy_hash':canonical_hash({'hypothesis':strategy.hypothesis_id,'runtime':strategy.spec.get('runtime',{})}),
                   'code_hash':implementation_hash(),'validated':False}
            db.add(SystemState(key=key,data=grant,updated_at=now))
            db.add(StrategyTransition(strategy_id=strategy.id,from_status='IDEA',to_status='DEMO_TESTING',
                actor='owner-demo-commissioning',actor_kind='owner',criteria='Collect broker demo forward evidence; unvalidated hypothesis',evidence={'demo_test_grant':key}))
            strategy.status='DEMO_TESTING'
            record(db,'owner-demo-commissioning','strategy.demo_test.authorized',{'strategy_id':strategy.id,**grant})
            configured.append(strategy.id)
    print(json.dumps({'configured':configured,'orders_submitted':0,'validated':False,'expires_in_days':7}))


if __name__=='__main__':configure()
