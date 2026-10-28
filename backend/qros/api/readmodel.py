"""Read-model assembly for the dashboard. Never fabricates values: anything not
backed by broker-observed or recorded data is returned as null with a reason."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from qros.config.settings import Settings
from qros.db.models import (AccountSnapshot, ControlState, PositionSnapshot, RiskDay, RiskStateRow,
                            ServiceHeartbeat, Trade)
from qros.risk.calendar import next_reset, trading_day
from qros.services import settings_store as st
from qros.services.settings_store import as_utc


def _age(now: datetime, t: Optional[datetime]) -> Optional[float]:
    t = as_utc(t)
    return None if t is None else round((now - t).total_seconds(), 1)


def connection_status(s: Session, settings: Settings, now: datetime) -> dict:
    hb = s.get(ServiceHeartbeat, "executor")
    if hb is None:
        return {"executor": "never_started", "broker_connected": False, "broker_adapter": None,
                "last_beat": None, "age_s": None, "detail": {}, "last_error": None,
                "summary": "Execution service has never run"}
    age = _age(now, hb.last_beat)
    alive = age is not None and age <= settings.stale_after_seconds
    connected = alive and hb.broker_connected and bool((hb.broker_detail or {}).get("snapshot_ok"))
    if not alive:
        summary = f"Execution service offline (last heartbeat {age:.0f}s ago)"
    elif not hb.broker_connected:
        summary = f"Broker disconnected: {hb.last_error or 'unknown reason'}"
    elif not connected:
        summary = "Broker connected but account snapshot failed"
    else:
        summary = "Connected"
    return {"executor": "online" if alive else "offline", "broker_connected": connected,
            "broker_adapter": hb.broker_adapter, "last_beat": as_utc(hb.last_beat).isoformat(),
            "age_s": age, "detail": hb.broker_detail or {}, "last_error": hb.last_error,
            "summary": summary}


def control_state(s: Session) -> dict:
    from qros.db.models import SystemState
    arm=s.get(SystemState,'demo_forward_arm')
    cs = s.get(ControlState, 1)
    if cs is None:
        return {"trading_mode": "off", "run_state": "stopped", "kill_switch": False,
                "halt_reason": None, "active_strategy_ids": []}
    return {"trading_mode": cs.trading_mode, "run_state": cs.run_state, "kill_switch": cs.kill_switch,
            "demo_forward_arm": arm.data if arm else None,
            "halt_reason": cs.halt_reason, "active_strategy_ids": cs.active_strategy_ids or [],
            "updated_at": as_utc(cs.updated_at).isoformat() if cs.updated_at else None}


def risk_state(s: Session, settings: Settings, now: datetime) -> dict:
    firm = st.active_firm(s)
    limits = st.internal_limits(s)
    rs = s.get(RiskStateRow, 1)
    nr = next_reset(now, firm.daily_reset)
    base = {"firm": firm.model_dump(mode="json"), "limits": limits.model_dump(mode="json"),
            "next_reset_utc": nr.isoformat(), "seconds_to_reset": int((nr - now).total_seconds()),
            "current_trading_day": trading_day(now, firm.daily_reset).isoformat()}
    if rs is None or rs.firm_id != firm.id:
        return {**base, "available": False, "stale": True, "computed_at": None, "age_s": None,
                "data": None, "reason": "No broker-observed account data for the active firm profile yet"}
    age = _age(now, rs.computed_at)
    return {**base, "available": True, "stale": age is None or age > settings.stale_after_seconds,
            "computed_at": as_utc(rs.computed_at).isoformat(), "age_s": age, "data": rs.data,
            "hwm_equity": rs.hwm_equity, "hwm_eod_balance": rs.hwm_eod_balance}


def _risk_status(rs: dict, ctrl: dict) -> str:
    if ctrl["kill_switch"]:
        return "kill_switch"
    if ctrl["run_state"] == "halted":
        return "halted"
    if not rs["available"] or rs["stale"]:
        return "unknown"
    d = rs["data"]
    if d.get("halt_required"):
        return "halt_required"
    if d.get("internal_daily_warning") or d.get("unprotected_tickets"):
        return "warning"
    return "ok"


def overview(s: Session, settings: Settings, now: datetime) -> dict:
    conn = connection_status(s, settings, now)
    ctrl = control_state(s)
    rs = risk_state(s, settings, now)
    firm = st.active_firm(s)
    acct: dict[str, Any] = {"available": False, "stale": True}
    pnl: dict[str, Any] = {"daily": None, "weekly": None, "weekly_since": None,
                           "weekly_note": None}
    if rs["available"]:
        d = rs["data"]
        acct = {"available": True, "stale": rs["stale"], "observed_at": rs["computed_at"],
                "balance": d["balance"], "equity": d["equity"], "currency": d.get("currency",firm.currency), "source": d.get("source"),
                "login": conn["detail"].get("login"), "server": conn["detail"].get("server"),
                "is_demo": conn["detail"].get("is_demo")}
        anchor_verified=d.get('anchor_method')=='observed_at_reset'
        pnl["daily"] = d["equity"] - d["sod_balance"] if anchor_verified else None
        if not anchor_verified:pnl['daily_note']='Firm reset anchor was not directly observed; P&L unavailable' 
        pnl["daily_anchor_method"] = d.get("anchor_method")
        # Weekly P/L only from recorded start-of-day anchors within this ISO week.
        today = date.fromisoformat(rs["current_trading_day"])
        monday = today - timedelta(days=today.weekday())
        first = s.execute(select(RiskDay).where(RiskDay.firm_id == d.get("risk_scope_key",firm.id),
                                                RiskDay.trading_day >= monday.isoformat())
                          .order_by(RiskDay.trading_day)).scalars().first()
        if first is not None and first.anchor_method=="observed_at_reset":
            pnl["weekly"] = d["equity"] - first.sod_balance
            pnl["weekly_since"] = first.trading_day
            if first.trading_day != monday.isoformat():
                pnl["weekly_note"] = "partial week: no anchor recorded before " + first.trading_day
        elif first is not None:
            pnl['weekly_note']='First weekly anchor was estimated; weekly P&L unavailable' 

    day_start = datetime.fromisoformat(rs["next_reset_utc"]) - timedelta(days=1)
    closed_today = s.execute(select(Trade).where(Trade.exit_time.is_not(None),
                                                 Trade.exit_time >= day_start)).scalars().all()
    opened_today = s.execute(select(func.count(Trade.id)).where(Trade.entry_time >= day_start)).scalar()
    all_closed = s.execute(select(Trade.pnl).where(Trade.pnl.is_not(None))).scalars().all()
    win_rate = (sum(1 for x in all_closed if x > 0) / len(all_closed)) if all_closed else None

    pos_rows = s.execute(select(PositionSnapshot)).scalars().all() if conn["broker_connected"] else None
    return {
        "server_time": now.isoformat(),
        "connection": conn,
        "control": ctrl,
        "account": acct,
        "pnl": pnl,
        "drawdown_buffer": (rs["data"]["remaining_to_effective_floor"] if rs["available"] else None),
        "risk_status": _risk_status(rs, ctrl),
        "trades_today": opened_today if opened_today else 0,
        "closed_trades_today": len(closed_today),
        "win_rate": win_rate,
        "win_rate_n": len(all_closed),
        "open_positions": (len(pos_rows) if pos_rows is not None else None),
        "firm": {"id": firm.id, "name": firm.name, "is_example": firm.is_example},
        "live_trading_enabled_on_host": settings.live_trading_enabled,
    }


def equity_curve(s: Session, since: Optional[datetime], limit: int = 5000) -> list[dict]:
    q = select(AccountSnapshot).order_by(AccountSnapshot.observed_at.desc()).limit(limit)
    if since is not None:
        q = q.where(AccountSnapshot.observed_at >= since)
    rows = list(reversed(s.execute(q).scalars().all()))
    return [{"t": as_utc(r.observed_at).isoformat(), "equity": r.equity, "balance": r.balance,
             "source": r.source} for r in rows]
