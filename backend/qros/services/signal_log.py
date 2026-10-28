"""Deduplicate decision logs by strategy/mode/bar/reason across restarts."""
import hashlib
from qros.db.models import SignalLog

def record_signal(db, runtime, decision, result, now):
    at = decision.completed_bar_at
    slot = (at or now.replace(minute=0,second=0,microsecond=0)).isoformat()
    mode = runtime.mode.value
    key = hashlib.sha256(f'{runtime.strategy_id}|{mode}|{slot}|{decision.reason}'.encode()).hexdigest()
    if db.get(SignalLog,key) is None:
        db.add(SignalLog(id=key,strategy_id=runtime.strategy_id,mode=mode,bar_time=at,
            reason=decision.reason,detail={'client_order_id':decision.client_order_id,'result':result},created_at=now))
