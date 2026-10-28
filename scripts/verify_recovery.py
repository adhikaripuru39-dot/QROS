"""Restore an actual online backup into an isolated, broker-free drill DB."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sqlite3,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select,func
from qros.config.settings import Settings
from qros.db.session import session_factory,session_scope
from qros.db.models import ControlState,OrderLedger,Trade
from qros.audit.log import verify_chain
from qros.broker.null_adapter import NullAdapter
from qros.services.executor import Executor

root=Path(__file__).resolve().parents[1]
source=sorted((root/'var/backups').glob('qros-*/qros.db'))[-1]
stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
target=root/'var/readiness'/('recovery-drill-'+stamp)/'restored.db'
target.parent.mkdir(parents=True,exist_ok=False)
with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True) as original:
    with sqlite3.connect(target) as restored:
        original.backup(restored)
        assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
settings=Settings(_env_file=None,database_url='sqlite:///'+target.as_posix(),
    broker_adapter='none',order_execution_enabled=False,live_trading_enabled=False)
factory=session_factory(settings.database_url)
with session_scope(factory) as db:
    original_chain=verify_chain(db);assert original_chain['ok']
    before={'orders':db.scalar(select(func.count(OrderLedger.client_order_id))),
            'trades':db.scalar(select(func.count(Trade.id)))}
    control=db.get(ControlState,1)
    control.trading_mode='demo';control.run_state='running'
    # Only the isolated restore is changed. No MT5 adapter is instantiated.
Executor(settings,NullAdapter(),factory).startup()
with session_scope(factory) as db:
    control=db.get(ControlState,1)
    assert control.run_state=='paused_entries'
    after={'orders':db.scalar(select(func.count(OrderLedger.client_order_id))),
           'trades':db.scalar(select(func.count(Trade.id)))}
    assert before==after
    chain=verify_chain(db);assert chain['ok']
report={'observed_at':datetime.now(timezone.utc).isoformat(),'backup':str(source),
    'backup_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'restored_to':str(target),'integrity_check':'ok','audit_chain':chain,
    'before':before,'after':after,'running_recovers_as':'paused_entries',
    'adapter':'none','broker_orders_submitted':0,'production_database_replaced':False}
(root/'var/readiness/recovery_acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
