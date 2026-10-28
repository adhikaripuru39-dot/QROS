"""Versioned, validated settings store (DB is source of truth after seeding)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from qros.audit.log import record
from qros.config.schemas import (FirmProfile, InstrumentConfig, InternalLimits, TradingHours,
                                 cross_validate)
from qros.config.settings import load_defaults, load_firm_profiles, load_instruments
from qros.db.models import ControlState, Setting, SettingHistory


class SettingsError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _get(s: Session, key: str) -> Optional[Setting]:
    return s.get(Setting, key)


def _put(s: Session, key: str, value: Any, actor: str) -> int:
    row = _get(s, key)
    if row is None:
        row = Setting(key=key, value=value, version=1)
        s.add(row)
    else:
        row.value = value
        row.version += 1
        row.updated_at = datetime.now(timezone.utc)
    s.add(SettingHistory(key=key, version=row.version, value=value, actor=actor))
    record(s, actor, "settings.update", {"key": key, "version": row.version, "value": value})
    s.flush()
    return row.version


def seed_if_empty(s: Session, config_dir=None) -> None:
    if _get(s, "firm_profiles") is not None:
        return
    defaults = load_defaults(config_dir)
    firms = {k: v.model_dump(mode="json") for k, v in load_firm_profiles(config_dir).items()}
    instruments = [i.model_dump(mode="json") for i in load_instruments(config_dir)]
    limits = InternalLimits.model_validate(defaults["internal_limits"]).model_dump(mode="json")
    hours = TradingHours.model_validate(defaults["trading_hours"]).model_dump(mode="json")
    if defaults["active_firm_id"] not in firms:
        raise SettingsError([f"active_firm_id {defaults['active_firm_id']} not found in config/firms"])
    _put(s, "firm_profiles", firms, "seed")
    _put(s, "active_firm_id", {"id": defaults["active_firm_id"]}, "seed")
    _put(s, "internal_limits", limits, "seed")
    _put(s, "instruments", {"items": instruments}, "seed")
    _put(s, "trading_hours", hours, "seed")
    if s.get(ControlState, 1) is None:
        s.add(ControlState(id=1, trading_mode="off", run_state="stopped", kill_switch=False))
    s.flush()


# ---- typed accessors --------------------------------------------------------

def firm_profiles(s: Session) -> dict[str, FirmProfile]:
    return {k: FirmProfile.model_validate(v) for k, v in _get(s, "firm_profiles").value.items()}


def active_firm(s: Session) -> FirmProfile:
    fid = _get(s, "active_firm_id").value["id"]
    return firm_profiles(s)[fid]


def internal_limits(s: Session) -> InternalLimits:
    return InternalLimits.model_validate(_get(s, "internal_limits").value)


def instruments(s: Session) -> list[InstrumentConfig]:
    return [InstrumentConfig.model_validate(x) for x in _get(s, "instruments").value["items"]]


def trading_hours(s: Session) -> TradingHours:
    return TradingHours.model_validate(_get(s, "trading_hours").value)


def version_of(s: Session, key: str) -> int:
    row = _get(s, key)
    return row.version if row else 0


# ---- validated writers -------------------------------------------------------

def upsert_firm_profile(s: Session, profile: dict, actor: str) -> FirmProfile:
    prof = FirmProfile.model_validate(profile)
    firms = {k: v.model_dump(mode="json") for k, v in firm_profiles(s).items()}
    if _get(s, "active_firm_id").value["id"] == prof.id:
        errs = cross_validate(prof, internal_limits(s))
        if errs:
            raise SettingsError(errs)
    firms[prof.id] = prof.model_dump(mode="json")
    _put(s, "firm_profiles", firms, actor)
    return prof


def set_active_firm(s: Session, firm_id: str, actor: str) -> FirmProfile:
    firms = firm_profiles(s)
    if firm_id not in firms:
        raise SettingsError([f"unknown firm profile '{firm_id}'"])
    errs = cross_validate(firms[firm_id], internal_limits(s))
    if errs:
        raise SettingsError(errs)
    _put(s, "active_firm_id", {"id": firm_id}, actor)
    return firms[firm_id]


def set_internal_limits(s: Session, data: dict, actor: str) -> InternalLimits:
    lim = InternalLimits.model_validate(data)
    errs = cross_validate(active_firm(s), lim)
    if errs:
        raise SettingsError(errs)
    _put(s, "internal_limits", lim.model_dump(mode="json"), actor)
    return lim


def set_instrument_enabled(s: Session, symbol: str, enabled: bool, actor: str) -> InstrumentConfig:
    items = instruments(s)
    found = None
    for i in items:
        if i.symbol == symbol:
            i.enabled = enabled
            found = i
    if found is None:
        raise SettingsError([f"unknown instrument '{symbol}'"])
    _put(s, "instruments", {"items": [i.model_dump(mode="json") for i in items]}, actor)
    return found


def update_instrument(s: Session, data: dict, actor: str) -> InstrumentConfig:
    new = InstrumentConfig.model_validate(data)
    items = instruments(s)
    if not any(i.symbol == new.symbol for i in items):
        raise SettingsError([f"unknown instrument '{new.symbol}'"])
    items = [new if i.symbol == new.symbol else i for i in items]
    _put(s, "instruments", {"items": [i.model_dump(mode="json") for i in items]}, actor)
    return new


def set_trading_hours(s: Session, data: dict, actor: str) -> TradingHours:
    th = TradingHours.model_validate(data)
    _put(s, "trading_hours", th.model_dump(mode="json"), actor)
    return th

