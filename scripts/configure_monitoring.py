"""Configure monitoring from actual read-only commissioning evidence, never approve trading."""
from pathlib import Path
import sys,json,secrets
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from qros.config.settings import Settings
from qros.config.schemas import FirmProfile
from qros.db.session import session_factory,session_scope
from qros.db.models import ControlState,Setting
from qros.services import settings_store as st
from qros.services.execution import set_state
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
report=json.loads((root/'var/readiness/commissioning.json').read_text(encoding='utf-8'))
initial=report.get('initial_capital_observed')
if not report.get('is_demo') or not initial or initial<=0:raise RuntimeError('Observed demo initial funding required')
env=root/'.env'
if not env.exists():
    env.write_text('\n'.join(['QROS_ENV=prod','QROS_API_TOKEN='+secrets.token_urlsafe(48),'QROS_BROKER_ADAPTER=mt5',r'QROS_MT5_PATH=C:/Program Files/FTMO Global Markets MT5 Terminal/terminal64.exe','QROS_LIVE_TRADING_ENABLED=false','QROS_ORDER_EXECUTION_ENABLED=false','QROS_RESUME_ON_RESTART=false','QROS_HALT_ACTION=flatten_managed','QROS_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173'])+'\n',encoding='utf-8')
settings=Settings(_env_file=env)
factory=session_factory(settings.database_url)
with session_scope(factory) as db:
    st.seed_if_empty(db,settings.config_dir)
    firm=st.active_firm(db).model_dump(mode='json')
    firm.update(id='ftmo_free_trial_provisional',name=f'FTMO Free Trial ${initial:,.0f} — programme unverified',is_example=True,initial_balance=initial,currency=report['currency'])
    firm['daily_loss']['pct']=3.;firm['max_loss'].update(pct=10.,drawdown_type='trailing_intraday',trail_lock_at_initial=False)
    firm['profit_target_pct']=5.;firm['min_trading_days']=2;firm['consistency_max_day_share']=.3
    # A provisional strict envelope is visibly marked unverified. It cannot authorize entries.
    st.upsert_firm_profile(db,firm,'commissioning');st.set_active_firm(db,firm['id'],'commissioning')
    set_state(db,'firm_rule_provenance',{'status':'unverified','account_programme':'Free Trial','known_initial_funding':initial,'source':'observed MT5 balance funding deal','programme_variant':'not confirmed','rules_source':'https://ftmo.com/en/ftmo-free-trial/','note':'Strict provisional envelope; not a claim of applicable account rules. Entry permission remains blocked.'},datetime.now(timezone.utc))
    specs=json.loads((root/'var/readiness/broker_specs.json').read_text(encoding='utf-8'))['symbols']
    for item in st.instruments(db):
        observed=specs.get(item.symbol)
        if not observed:continue
        value=item.model_dump(mode='json')
        mapping={'point':'point','tick_size':'trade_tick_size','tick_value_per_lot':'trade_tick_value_loss','volume_min':'volume_min','volume_max':'volume_max','volume_step':'volume_step','min_stop_points':'trade_stops_level','contract_size':'trade_contract_size'}
        for target,source in mapping.items():
            observed_value=observed.get(source)
            if observed_value is not None and (observed_value>0 or target=='min_stop_points'):value[target]=observed_value
        st.update_instrument(db,value,'commissioning')
    ctrl=db.get(ControlState,1);ctrl.trading_mode='off';ctrl.run_state='stopped';ctrl.active_strategy_ids=[]
print('Monitoring configured from observed demo funding/specifications. Private token saved; order execution remains disabled.')
