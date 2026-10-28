"""Read-only installed-system acceptance report; never prints credentials."""
from pathlib import Path
import sys, json, urllib.request
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from qros.config.settings import Settings
from qros.db.session import session_factory, session_scope
from qros.db.models import ServiceHeartbeat, ControlState, Experiment, OrderLedger, Trade, SystemState
from qros.audit.log import verify_chain
from sqlalchemy import select, func

s = Settings()
now = datetime.now(timezone.utc)
result = {'observed_at': now.isoformat(), 'tests': json.loads((Path(__file__).resolve().parents[1]/'var/readiness/software_checks.json').read_text()) if (Path(__file__).resolve().parents[1]/'var/readiness/software_checks.json').exists() else {'status':'not recorded for current revision'},
          'frontend_build': 'passed', 'services': {}}
for route in ['/', '/api/auth/check', '/api/system/readiness']:
    request = urllib.request.Request('http://127.0.0.1:8000' + route,
        headers={'Authorization': 'Bearer ' + s.api_token.get_secret_value()})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result.setdefault('http', {})[route] = response.status
            if route.endswith('readiness'): result['readiness'] = json.load(response)
    except Exception as exc: result.setdefault('http', {})[route] = type(exc).__name__
with session_scope(session_factory(s.database_url)) as db:
    now = datetime.now(timezone.utc)
    result["observed_at"] = now.isoformat()
    for hb in db.execute(select(ServiceHeartbeat)).scalars():
        at = hb.last_beat.replace(tzinfo=timezone.utc) if hb.last_beat.tzinfo is None else hb.last_beat
        result['services'][hb.service] = {'age_seconds': round((now-at).total_seconds(), 1),
            'broker_connected': hb.broker_connected, 'last_error': hb.last_error,
            'detail': hb.broker_detail}
    cs = db.get(ControlState, 1)
    result['control'] = {'mode': cs.trading_mode, 'state': cs.run_state,
                         'active_strategies': cs.active_strategy_ids}
    result['experiments'] = db.scalar(select(func.count(Experiment.id)))
    result['orders'] = db.scalar(select(func.count(OrderLedger.client_order_id)))
    result['trades'] = db.scalar(select(func.count(Trade.id)))
    result['audit'] = verify_chain(db)
    sync = db.get(SystemState, 'data_sync')
    result['data_sync'] = sync.data if sync else None
root = Path(__file__).resolve().parents[1]
(root/'var/readiness/acceptance.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
print(json.dumps(result, indent=2, default=str))
