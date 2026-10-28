"""Append-only, SHA-256 hash-chained audit log.

Each record's hash covers (prev_hash, ts, actor, event, canonical JSON data).
``verify_chain`` recomputes the chain and reports the first broken link, so any
retroactive edit or deletion of an audit row is detectable.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from qros.db.models import AuditLog

GENESIS = "0" * 64


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _ts_str(ts: datetime) -> str:
    if ts.tzinfo is None:  # SQLite returns naive datetimes; we always store UTC
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _hash(prev: str, ts: datetime, actor: str, event: str, data: Any) -> str:
    h = hashlib.sha256()
    h.update("|".join([prev, _ts_str(ts), actor, event, _canonical(data)]).encode())
    return h.hexdigest()


def record(s: Session, actor: str, event: str, data: dict | None = None) -> AuditLog:
    data = json.loads(_canonical(data or {}))
    connection=s.connection()
    if connection.dialect.name=='postgresql':
        connection.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':770001530})
    elif connection.dialect.name=='sqlite':
        raw=connection.connection.driver_connection
        if not raw.in_transaction:connection.exec_driver_sql('BEGIN IMMEDIATE')
    last = s.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none()
    prev = last.hash if last else GENESIS
    ts = datetime.now(timezone.utc)
    row = AuditLog(ts=ts, actor=actor, event=event, data=data, prev_hash=prev,
                   hash=_hash(prev, ts, actor, event, data))
    s.add(row)
    s.flush()
    return row


def verify_chain(s: Session) -> dict:
    prev = GENESIS
    n = 0
    for row in s.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        if row.prev_hash != prev or _hash(prev, row.ts, row.actor, row.event, row.data) != row.hash:
            return {"ok": False, "checked": n, "broken_at_id": row.id}
        prev = row.hash
        n += 1
    return {"ok": True, "checked": n, "broken_at_id": None}
