"""Strategy registry, governance, research (Phase 2 stub), journal."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from qros.audit.log import record
from qros.db.models import Experiment, Strategy, StrategyTransition, Trade
from qros.governance.lifecycle import TRANSITIONS, StrategyStatus, TransitionError, check_transition
from qros.reporting.stats import ClosedTrade, summarize
from qros.services.settings_store import as_utc

from .deps import get_db, require_owner, require_owner_query

router = APIRouter(prefix="/api")


# ---- governance ---------------------------------------------------------------
@router.get("/governance/lifecycle")
def lifecycle(_: str = Depends(require_owner)):
    return {s.value: [{"target": r.target.value, "criteria": r.criteria,
                       "required_evidence": list(r.required_evidence), "owner_only": r.owner_only}
                      for r in rules] for s, rules in TRANSITIONS.items()}


def _strategy(s: Strategy) -> dict:
    return {"id": s.id, "hypothesis_id": s.hypothesis_id, "family": s.family, "name": s.name,
            "status": s.status, "spec": s.spec, "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat()}


@router.get("/strategies")
def list_strategies(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return [_strategy(s) for s in db.execute(select(Strategy).order_by(Strategy.id)).scalars()]


@router.get("/strategies/{sid}")
def get_strategy(sid: str, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    s = db.get(Strategy, sid)
    if s is None:
        raise HTTPException(404, "strategy not found")
    tr = db.execute(select(StrategyTransition).where(StrategyTransition.strategy_id == sid)
                    .order_by(StrategyTransition.id)).scalars()
    return {**_strategy(s), "transitions": [
        {"from": t.from_status, "to": t.to_status, "actor": t.actor, "actor_kind": t.actor_kind,
         "evidence": t.evidence, "criteria": t.criteria, "at": t.created_at.isoformat()} for t in tr]}


class TransitionIn(BaseModel):
    target: StrategyStatus
    evidence: dict[str, str] = Field(default_factory=dict)


@router.post("/strategies/{sid}/transition")
def transition(sid: str, body: TransitionIn, db: Session = Depends(get_db), actor: str = Depends(require_owner)):
    s = db.get(Strategy, sid)
    if s is None:
        raise HTTPException(404, "strategy not found")
    try:
        rule = check_transition(StrategyStatus(s.status), body.target, "owner", body.evidence)
    except TransitionError as e:
        raise HTTPException(422, {"errors": [str(e)]})
    from qros.services.evidence import transition_evidence
    errors=transition_evidence(db,s,body.target.value,body.evidence)
    if errors:raise HTTPException(422,{"errors":errors})
    if body.target.value=='VALIDATED':
        from qros.db.models import EvidenceReport
        report=db.get(EvidenceReport,body.evidence['validation_report_id'])
        s.spec={**s.spec,'validation_report_id':report.id,'validated_config_hash':report.config_hash}
    if body.target.value=='DEMO_APPROVED':s.spec={**s.spec,'paper_report_id':body.evidence['paper_report_id']}
    if body.target.value=='LIVE_APPROVED':s.spec={**s.spec,'demo_report_id':body.evidence['demo_report_id']}
    db.add(StrategyTransition(strategy_id=sid, from_status=s.status, to_status=body.target.value, actor=actor,
                              actor_kind="owner", evidence=body.evidence, criteria=rule.criteria))
    record(db, actor, "strategy.transition", {"strategy_id": sid, "from": s.status, "to": body.target.value,
                                               "evidence": body.evidence})
    s.status, s.updated_at = body.target.value, datetime.now(timezone.utc)
    return _strategy(s)


# ---- research (Phase 2) ----------------------------------------------------------
@router.get("/research/experiments")
def experiments(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    rows = db.execute(select(Experiment).order_by(Experiment.created_at.desc())).scalars()
    return [{"id": e.id, "hypothesis_id": e.hypothesis_id, "kind": e.kind, "status": e.status,
             "progress": e.progress, "dataset_version": e.dataset_version, "code_version": e.code_version,
             "seed": e.seed, "results": e.results, "failure_reason": e.failure_reason,
             "created_at": e.created_at.isoformat(),
             "finished_at": e.finished_at.isoformat() if e.finished_at else None} for e in rows]


@router.get("/research/status")
def research_status(_: str = Depends(require_owner)):
    return {"implemented": True, "phase": 3,
            "message": "Historical ingestion, backtesting, research and validation modules are implemented. Jobs run in the independent worker. No strategy is approved without verified evidence and owner deployment approval."}


# ---- journal --------------------------------------------------------------------------
def _trade(t: Trade) -> dict:
    return {"id": t.id, "mode": t.mode, "strategy_id": t.strategy_id, "symbol": t.symbol, "side": t.side,
            "volume": t.volume, "entry_time": as_utc(t.entry_time).isoformat(), "entry_price": t.entry_price,
            "intended_entry": t.intended_entry, "sl": t.sl, "tp": t.tp,
            "exit_time": as_utc(t.exit_time).isoformat() if t.exit_time else None, "exit_price": t.exit_price,
            "pnl": t.pnl, "commission": t.commission, "swap": t.swap, "slippage_points": t.slippage_points,
            "risk_amount": t.risk_amount, "reason": t.reason, "exit_reason": t.exit_reason,
            "broker_ticket": t.broker_ticket}


@router.get("/journal/trades")
def trades(limit: int = Query(500, le=5000), db: Session = Depends(get_db), _: str = Depends(require_owner)):
    rows = db.execute(select(Trade).order_by(Trade.entry_time.desc()).limit(limit)).scalars()
    return [_trade(t) for t in rows]


@router.get("/journal/stats")
def stats(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    rows = db.execute(select(Trade).where(Trade.pnl.is_not(None), Trade.exit_time.is_not(None))).scalars()
    return summarize(ClosedTrade(t.symbol, t.strategy_id, as_utc(t.exit_time), t.pnl, t.slippage_points)
                     for t in rows)


@router.get("/journal/export.csv")
def export_csv(db: Session = Depends(get_db), _: str = Depends(require_owner_query)):
    rows = [_trade(t) for t in db.execute(select(Trade).order_by(Trade.entry_time)).scalars()]
    buf = io.StringIO()
    cols = list(_trade.__annotations__) or None
    fields = ["id", "mode", "strategy_id", "symbol", "side", "volume", "entry_time", "entry_price",
              "intended_entry", "sl", "tp", "exit_time", "exit_price", "pnl", "commission", "swap",
              "slippage_points", "risk_amount", "reason", "exit_reason", "broker_ticket"]
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=qros_trades.csv"})
