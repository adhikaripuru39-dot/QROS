"""Core read endpoints: health, overview, equity curve, SSE stream, audit."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from qros import __version__
from qros.audit.log import verify_chain
from qros.db.models import AuditLog

from . import readmodel as rm
from .deps import get_app_settings, get_db, require_owner, require_owner_query

router = APIRouter(prefix="/api")


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/health")
def health(request: Request):
    return {"status": "ok", "version": __version__, "time": _now().isoformat(),
            "env": request.app.state.settings.env}


@router.get("/auth/check")
def auth_check(actor: str = Depends(require_owner)):
    return {"ok": True, "actor": actor}


@router.get("/overview")
def get_overview(db: Session = Depends(get_db), settings=Depends(get_app_settings),
                 _: str = Depends(require_owner)):
    return rm.overview(db, settings, _now())


@router.get("/equity-curve")
def get_equity_curve(since: Optional[datetime] = None, limit: int = Query(5000, le=20000),
                     db: Session = Depends(get_db), _: str = Depends(require_owner)):
    pts = rm.equity_curve(db, since, limit)
    return {"available": bool(pts), "points": pts,
            "note": None if pts else "No broker-observed account snapshots recorded yet"}


@router.get("/stream")
async def stream(request: Request, _: str = Depends(require_owner_query)):
    settings = request.app.state.settings
    factory = request.app.state.session_factory

    async def gen():
        while not await request.is_disconnected():
            s = factory()
            try:
                payload = rm.overview(s, settings, _now())
            finally:
                s.close()
            yield f"event: overview\ndata: {json.dumps(payload, default=str)}\n\n"
            await asyncio.sleep(2.0)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/audit")
def audit(limit: int = Query(200, le=2000), event: Optional[str] = None,
          db: Session = Depends(get_db), _: str = Depends(require_owner)):
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if event:
        q = q.where(AuditLog.event.like(f"{event}%"))
    return [{"id": r.id, "ts": r.ts.isoformat(), "actor": r.actor, "event": r.event, "data": r.data,
             "hash": r.hash} for r in db.execute(q).scalars()]


@router.get("/audit/verify")
def audit_verify(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return verify_chain(db)
