"""Apply owner-confirmed programme; never grants execution or strategy approval."""
from pathlib import Path
import sys
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from qros.config.settings import Settings, load_firm_profiles
from qros.db.session import session_factory, session_scope
from qros.db.models import ControlState
from qros.services import settings_store as st
from qros.services.execution import set_state

settings = Settings()
profile = load_firm_profiles(settings.config_dir)['ftmo_free_trial_50k_2step']
with session_scope(session_factory(settings.database_url)) as db:
    ctrl = db.get(ControlState, 1)
    if ctrl is None or ctrl.run_state not in ('stopped', 'paused_entries'):
        raise RuntimeError('Stop the executor before commissioning account rules')
    st.upsert_firm_profile(db, profile.model_dump(mode='json'), 'owner-confirmed-commissioning')
    st.set_active_firm(db, profile.id, 'owner-confirmed-commissioning')
    set_state(db, 'firm_rule_provenance', {
        'status': 'programme_confirmed_published_rules_applied',
        'account_programme': '2-Step Free Trial',
        'initial_capital': 50000, 'initial_capital_source': 'observed MT5 funding deal',
        'programme_source': 'Owner confirmation on 2026-10-23',
        'sources': ['https://ftmo.com/en/ftmo-free-trial/',
                    'https://ftmo.com/en/trading-objectives/',
                    'https://ftmo.com/en/faq/can-i-trade-news/',
                    'https://ftmo.com/en/faq/can-i-hold-positions-overnight-or-over-the-weekend/'],
        'fee_schedule_verified': False,
        'commission_assumption_round_turn_per_lot': 7.0,
        'trial_expiry_verified': False,
        'note': '14-day trial expiry not inferred from funding time. No execution permission granted.'
    }, datetime.now(timezone.utc))
    ctrl.trading_mode = 'off'
    ctrl.run_state = 'stopped'
    ctrl.active_strategy_ids = []
print('Applied confirmed FTMO 2-Step Free Trial rules. Execution remains OFF.')
