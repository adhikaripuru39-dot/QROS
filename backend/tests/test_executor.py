from datetime import datetime,timezone
from qros.broker.null_adapter import NullAdapter
from qros.config.settings import Settings
from qros.db.models import ControlState,ControlCommand,ServiceHeartbeat
from qros.db.session import session_scope
from qros.services.executor import Executor
from qros.audit.log import verify_chain

def make_executor(factory):
    return Executor(Settings(_env_file=None),NullAdapter(),factory)

def test_restart_pauses_previously_running_session(factory):
    ex=make_executor(factory);ex.startup()
    with session_scope(factory) as db:db.get(ControlState,1).run_state='running'
    ex.startup()
    with session_scope(factory) as db:
        assert db.get(ControlState,1).run_state=='paused_entries'
        assert verify_chain(db)['ok']

def test_disconnected_heartbeat_is_truthful(factory):
    ex=make_executor(factory);ex.startup();ex.tick()
    with session_scope(factory) as db:
        hb=db.get(ServiceHeartbeat,'executor')
        assert hb is not None and not hb.broker_connected
        assert db.get(ControlState,1).trading_mode=='off'

def test_disconnected_kill_stays_engaged_and_reports_failure(factory):
    ex=make_executor(factory);ex.startup()
    with session_scope(factory) as db:
        cmd=ControlCommand(command='kill',payload={'confirm':'KILL'},actor='owner',status='pending')
        db.add(cmd);db.flush();cid=cmd.id
    ex.tick()
    with session_scope(factory) as db:
        assert db.get(ControlState,1).kill_switch
        cmd=db.get(ControlCommand,cid)
        assert cmd.status=='failed' and cmd.result['failures']
        assert verify_chain(db)['ok']

def test_start_cannot_bypass_missing_risk_and_mode(factory):
    ex=make_executor(factory);ex.startup()
    with session_scope(factory) as db:
        cmd=ControlCommand(command='start',payload={},actor='owner',status='pending')
        db.add(cmd);db.flush();cid=cmd.id
    ex.tick()
    with session_scope(factory) as db:
        assert db.get(ControlCommand,cid).status=='rejected'
        assert db.get(ControlState,1).run_state=='stopped'
