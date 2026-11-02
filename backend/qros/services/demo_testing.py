"""Expiring owner permission to collect real broker DEMO observations.

This is not validation or permission for funded accounts. Grants are immutable
snapshots; changing account, runtime, implementation or limits invalidates them.
"""
from datetime import datetime, timezone
import math
from qros.db.models import SystemState
from qros.services.evidence import canonical_hash
from qros.research.runner import implementation_hash
from qros.services import settings_store as st


def grant_errors(db, strategy, mode, now=None, account=None, settings=None):
    if mode != 'demo':
        return ['DEMO_TESTING_FORBIDDEN_OUTSIDE_DEMO']
    now = now or datetime.now(timezone.utc)
    row = db.get(SystemState, 'demo_test_grant:' + strategy.id)
    if row is None:
        return ['DEMO_TEST_OWNER_GRANT_MISSING']
    g = row.data
    errors = []
    try:
        start = datetime.fromisoformat(g['authorized_at'])
        end = datetime.fromisoformat(g['expires_at'])
        if start.tzinfo is None or end.tzinfo is None or not start <= now < end or (end-start).total_seconds() > 8*86400:
            errors.append('DEMO_TEST_GRANT_EXPIRED_OR_INVALID')
        if g['actor_kind'] != 'owner' or not isinstance(g.get('programme'), str) or not g['programme'].strip() or g['funded'] is not False:
            errors.append('DEMO_TEST_OWNER_SCOPE_INVALID')
        if g['strategy_hash'] != canonical_hash({'hypothesis':strategy.hypothesis_id,'runtime':strategy.spec.get('runtime',{})}):
            errors.append('DEMO_TEST_RUNTIME_CHANGED')
        if g['code_hash'] != implementation_hash():
            errors.append('DEMO_TEST_CODE_CHANGED')
        if g['firm_id'] != st.active_firm(db).id:
            errors.append('DEMO_TEST_FIRM_CHANGED')
        limits = st.internal_limits(db)
        ml = g.get('max_limits') or {}
        if (limits.risk_per_trade_pct > float(ml.get('risk_per_trade_pct', .05)) or
                limits.max_open_positions > int(ml.get('max_open_positions', 1)) or
                limits.max_trades_per_day > int(ml.get('max_trades_per_day', 6)) or
                limits.daily_stop_pct > float(ml.get('daily_stop_pct', .5)) or
                limits.max_total_open_risk_pct > float(ml.get('max_total_open_risk_pct', .1))):
            errors.append('DEMO_TEST_LIMITS_EXCEEDED')
        if settings is not None and (not settings.news_filter_enabled or settings.live_trading_enabled):
            errors.append('DEMO_TEST_REQUIRES_NEWS_AND_LIVE_DISABLED')
        if account is not None:
            from qros.services.execution import account_key
            from qros.services.account_rules import account_rule_errors
            if (account.is_demo is not True or account.server != g['server'] or
                    account_key(account,'demo') != g['account_key']):
                errors.append('DEMO_TEST_ACCOUNT_MISMATCH')
            errors.extend(account_rule_errors(db,st.active_firm(db),account.server,account.login))
            if not math.isfinite(account.balance) or account.balance <= 0:
                errors.append('DEMO_TEST_ACCOUNT_INVALID')
    except (KeyError, TypeError, ValueError, OverflowError):
        errors.append('DEMO_TEST_GRANT_MALFORMED')
    return errors
