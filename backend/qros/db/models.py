"""SQLAlchemy ORM models (SQLite dev / PostgreSQL-compatible)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SettingHistory(Base):
    __tablename__ = "settings_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    value: Mapped[dict[str, Any]] = mapped_column(JSON)
    actor: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ControlState(Base):
    """Single-row (id=1). Written ONLY by the executor service."""
    __tablename__ = "control_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trading_mode: Mapped[str] = mapped_column(String(16), default="off")
    run_state: Mapped[str] = mapped_column(String(32), default="stopped")
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    halt_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_strategy_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ControlCommand(Base):
    __tablename__ = "control_commands"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    actor: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|done|rejected|failed
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeat"
    service: Mapped[str] = mapped_column(String(32), primary_key=True)
    pid: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_beat: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    broker_adapter: Mapped[str] = mapped_column(String(16))
    broker_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    broker_detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(16))  # mt5 | paper
    login: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    server: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_demo: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    currency: Mapped[str] = mapped_column(String(8))
    balance: Mapped[float] = mapped_column(Float)
    equity: Mapped[float] = mapped_column(Float)
    margin: Mapped[float] = mapped_column(Float)
    free_margin: Mapped[float] = mapped_column(Float)
    leverage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class PositionSnapshot(Base):
    __tablename__ = "positions_snapshot"
    ticket: Mapped[str] = mapped_column(String(32), primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    symbol: Mapped[str] = mapped_column(String(16))
    side: Mapped[str] = mapped_column(String(4))
    volume: Mapped[float] = mapped_column(Float)
    price_open: Mapped[float] = mapped_column(Float)
    sl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit: Mapped[float] = mapped_column(Float)
    magic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    risk_to_stop: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class RiskDay(Base):
    __tablename__ = "risk_days"
    __table_args__ = (UniqueConstraint("firm_id", "trading_day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    firm_id: Mapped[str] = mapped_column(String(64))
    trading_day: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD firm-local
    sod_balance: Mapped[float] = mapped_column(Float)
    sod_equity: Mapped[float] = mapped_column(Float)
    anchor_method: Mapped[str] = mapped_column(String(32))  # observed_at_reset | reconstructed_from_deals | conservative_estimate
    eod_balance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RiskStateRow(Base):
    __tablename__ = "risk_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # single row id=1
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    firm_id: Mapped[str] = mapped_column(String(64))
    trading_day: Mapped[str] = mapped_column(String(10))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    hwm_equity: Mapped[float] = mapped_column(Float)
    hwm_eod_balance: Mapped[float] = mapped_column(Float)


class Strategy(Base):
    __tablename__ = "strategies"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hypothesis_id: Mapped[str] = mapped_column(String(64))
    family: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="IDEA")
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StrategyTransition(Base):
    __tablename__ = "strategy_transitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), index=True)
    from_status: Mapped[str] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(64))
    actor_kind: Mapped[str] = mapped_column(String(16))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    criteria: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hypothesis_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # backtest | validation | walkforward | oos
    status: Mapped[str] = mapped_column(String(16))  # queued|running|completed|failed|rejected
    code_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    dataset_version: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    results: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str] = mapped_column(String(8))  # paper|demo|live
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16))
    side: Mapped[str] = mapped_column(String(4))
    volume: Mapped[float] = mapped_column(Float)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[float] = mapped_column(Float)
    intended_entry: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    swap: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text)  # why the trade occurred (signal explanation)
    exit_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    broker_ticket: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, unique=True)
    client_order_id: Mapped[str] = mapped_column(String(64), unique=True)  # duplicate-order protection


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))

class OrderLedger(Base):
    """Durable intent recorded BEFORE any broker submission. Unknown is never retried."""
    __tablename__ = "order_ledger"
    client_order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_key: Mapped[str] = mapped_column(String(128), index=True)
    strategy_id: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(24), index=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSON)
    decision: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BrokerDeal(Base):
    __tablename__ = "broker_deals"
    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    account_key: Mapped[str] = mapped_column(String(128), index=True)
    position_id: Mapped[str] = mapped_column(String(32), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)


class SystemState(Base):
    __tablename__ = "system_state"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True, default="queued")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvidenceReport(Base):
    __tablename__ = "evidence_reports"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    passed: Mapped[bool] = mapped_column(Boolean)
    dataset_hash: Mapped[str] = mapped_column(String(64))
    code_hash: Mapped[str] = mapped_column(String(64))
    config_hash: Mapped[str] = mapped_column(String(64))
    report_hash: Mapped[str] = mapped_column(String(64))
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SignalLog(Base):
    __tablename__ = "signal_logs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(8))
    bar_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(160))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
