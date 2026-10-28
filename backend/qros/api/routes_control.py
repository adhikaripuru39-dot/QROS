"""Trading control: the API only ENQUEUES commands; the executor decides.

The response reflects the executor's actual decision if it arrives within the
wait window, otherwise status stays 'pending' (and the UI says so).
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from qros.audit.log import record
from qros.db.models import ControlCommand
from qros.services.executor import KILL_RELEASE_PHRASE, LIVE_CONFIRM_PHRASE, RESUME_PHRASE

from . import readmodel as rm
from .deps import get_db, require_owner

router = APIRouter(prefix="/api/control")

COMMANDS: dict[str, dict[str, Any]] = {
    "arm_demo": {"label": "Arm demo when ready", "effect": "Queues a one-time start for account-bound DEMO_TESTING experiments after every demo readiness check passes. Manual commands and executor restart cancel the pending arm."},
    "start": {"label": "Start trading",
              "effect": "Allows the signal engine to submit NEW entries for active strategies, subject to "
                        "every risk-engine check. Resuming from HALTED requires typing RESUME."},
    "pause_entries": {"label": "Pause new entries",
                      "effect": "Blocks new entries. Open positions, broker-side stops and targets unchanged."},
    "stop": {"label": "Stop trading",
             "effect": "Stops strategy evaluation. Open positions are NOT closed; broker-side stops remain."},
    "kill": {"label": "Emergency kill switch",
             "effect": "Engages kill flag (blocks all orders), cancels ALL pending orders on the account and "
                       "attempts to close ALL open positions at market. Every failure is reported. Requires "
                       "typing KILL.", "confirm": "KILL"},
    "release_kill": {"label": "Release kill switch",
                     "effect": "Clears kill flag; run state becomes STOPPED. Does not start trading.",
                     "confirm": KILL_RELEASE_PHRASE},
    "set_mode": {"label": "Set trading mode",
                 "effect": "Changes Off/Paper/Demo/Live. Trading must be stopped first. Demo requires a demo "
                           "account; Live requires host enablement, a real account, a LIVE_APPROVED strategy "
                           f"and typing '{LIVE_CONFIRM_PHRASE}'."},
    "set_active_strategies": {"label": "Set active strategies",
                              "effect": "Selects which strategies may generate signals. Each must have a "
                                        "lifecycle status permitted in the current mode."},
}


class CommandIn(BaseModel):
    command: str
    payload: dict = Field(default_factory=dict)
    confirm: Optional[str] = None
    wait_seconds: float = Field(default=6.0, ge=0, le=15)


def _row(c: ControlCommand) -> dict:
    return {"id": c.id, "command": c.command, "payload": c.payload, "actor": c.actor, "status": c.status,
            "result": c.result, "created_at": c.created_at.isoformat(),
            "processed_at": c.processed_at.isoformat() if c.processed_at else None}


@router.get("/state")
def state(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return {**rm.control_state(db), "commands": COMMANDS,
            "phrases": {"resume": RESUME_PHRASE, "live": LIVE_CONFIRM_PHRASE, "release_kill": KILL_RELEASE_PHRASE}}


@router.get("/commands")
def list_commands(limit: int = Query(50, le=500), db: Session = Depends(get_db), _: str = Depends(require_owner)):
    rows = db.execute(select(ControlCommand).order_by(ControlCommand.id.desc()).limit(limit)).scalars()
    return [_row(c) for c in rows]


@router.post("/commands")
async def submit(body: CommandIn, db: Session = Depends(get_db), actor: str = Depends(require_owner)):
    spec = COMMANDS.get(body.command)
    if spec is None:
        raise HTTPException(422, {"errors": [f"unknown command '{body.command}'"]})
    if "confirm" in spec and body.confirm != spec["confirm"]:
        raise HTTPException(422, {"errors": [f"confirmation required: type '{spec['confirm']}'"]})
    payload = dict(body.payload)
    if body.confirm:
        payload["confirm"] = body.confirm
    if body.command == "set_mode" and payload.get("mode") == "live" and body.confirm != LIVE_CONFIRM_PHRASE:
        raise HTTPException(422, {"errors": [f"confirmation required: type '{LIVE_CONFIRM_PHRASE}'"]})
    c = ControlCommand(command=body.command, payload=payload, actor=actor, status="pending")
    db.add(c)
    db.flush()
    record(db, actor, f"command.{body.command}.requested", {"command_id": c.id, "payload": payload})
    db.commit()
    cid = c.id
    waited = 0.0
    while waited < body.wait_seconds:
        await asyncio.sleep(0.25)
        waited += 0.25
        db.expire_all()
        c = db.get(ControlCommand, cid)
        if c.status != "pending":
            break
    out = _row(c)
    if c.status == "pending":
        out["note"] = "Executor has not processed this command yet (is the execution service running?)"
    return out
