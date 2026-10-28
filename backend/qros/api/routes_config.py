"""Configuration + risk endpoints. All writes are validated and audited."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from qros.audit.log import record
from qros.config.schemas import FirmProfile, InternalLimits, cross_validate
from qros.db.models import Setting
from qros.services import settings_store as st
from qros.services.settings_store import SettingsError

from . import readmodel as rm
from .deps import get_app_settings, get_db, require_owner

router = APIRouter(prefix="/api")


def _guard(fn):
    try:
        return fn()
    except SettingsError as e:
        raise HTTPException(422, {"errors": e.errors})
    except ValidationError as e:
        raise HTTPException(422, {"errors": [f"{'.'.join(map(str, x['loc']))}: {x['msg']}"
                                             for x in e.errors()]})


# ---- instruments -------------------------------------------------------------
@router.get("/instruments")
def list_instruments(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return [i.model_dump(mode="json") for i in st.instruments(db)]


class EnablePatch(BaseModel):
    enabled: bool


@router.patch("/instruments/{symbol}")
def patch_instrument(symbol: str, body: EnablePatch, db: Session = Depends(get_db),
                     actor: str = Depends(require_owner)):
    return _guard(lambda: st.set_instrument_enabled(db, symbol, body.enabled, actor)).model_dump(mode="json")


@router.put("/instruments/{symbol}")
def put_instrument(symbol: str, body: dict, db: Session = Depends(get_db), actor: str = Depends(require_owner)):
    if body.get("symbol") != symbol:
        raise HTTPException(422, {"errors": ["symbol in body must match path"]})
    return _guard(lambda: st.update_instrument(db, body, actor)).model_dump(mode="json")


# ---- firm profiles & internal limits ------------------------------------------------
@router.get("/firms")
def list_firms(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    active = st.active_firm(db).id
    return {"active_id": active, "profiles": [p.model_dump(mode="json") for p in st.firm_profiles(db).values()]}


@router.put("/firms/{firm_id}")
def put_firm(firm_id: str, body: dict, db: Session = Depends(get_db), actor: str = Depends(require_owner)):
    if body.get("id") != firm_id:
        raise HTTPException(422, {"errors": ["id in body must match path"]})
    return _guard(lambda: st.upsert_firm_profile(db, body, actor)).model_dump(mode="json")


class ActiveFirm(BaseModel):
    id: str


@router.post("/firms/active")
def set_active(body: ActiveFirm, db: Session = Depends(get_db), actor: str = Depends(require_owner)):
    return _guard(lambda: st.set_active_firm(db, body.id, actor)).model_dump(mode="json")


@router.get("/limits")
def get_limits(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return st.internal_limits(db).model_dump(mode="json")


@router.put("/limits")
def put_limits(body: dict, db: Session = Depends(get_db), actor: str = Depends(require_owner)):
    return _guard(lambda: st.set_internal_limits(db, body, actor)).model_dump(mode="json")


class ValidateBody(BaseModel):
    firm: Optional[dict] = None
    limits: Optional[dict] = None


@router.post("/risk/validate")
def validate_config(body: ValidateBody, db: Session = Depends(get_db), _: str = Depends(require_owner)):
    """Dry-run validation of a firm profile and/or internal limits (nothing is saved)."""
    def run():
        firm = FirmProfile.model_validate(body.firm) if body.firm else st.active_firm(db)
        lim = InternalLimits.model_validate(body.limits) if body.limits else st.internal_limits(db)
        errs = cross_validate(firm, lim)
        return {"ok": not errs, "errors": errs}
    try:
        return _guard(run)
    except HTTPException as e:
        return {"ok": False, "errors": e.detail["errors"]}


@router.get("/trading-hours")
def get_hours(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    return st.trading_hours(db).model_dump(mode="json")


@router.put("/trading-hours")
def put_hours(body: dict, db: Session = Depends(get_db), actor: str = Depends(require_owner)):
    return _guard(lambda: st.set_trading_hours(db, body, actor)).model_dump(mode="json")


class Anchors(BaseModel):
    hwm_equity: Optional[float] = Field(default=None, gt=0)
    hwm_eod_balance: Optional[float] = Field(default=None, gt=0)


@router.put("/risk/anchors")
def put_anchors(body: Anchors, db: Session = Depends(get_db), actor: str = Depends(require_owner)):
    """Owner-entered high-water marks from the firm's own dashboard. Can only tighten limits."""
    row = db.get(Setting, "account_anchors")
    val = body.model_dump()
    if row is None:
        db.add(Setting(key="account_anchors", value=val, version=1))
    else:
        row.value, row.version = val, row.version + 1
    record(db, actor, "risk.anchors.update", val)
    return val


@router.get("/risk/state")
def get_risk_state(db: Session = Depends(get_db), settings=Depends(get_app_settings),
                   _: str = Depends(require_owner)):
    now = datetime.now(timezone.utc)
    out = rm.risk_state(db, settings, now)
    row = db.get(Setting, "account_anchors")
    out["anchors"] = row.value if row else {"hwm_equity": None, "hwm_eod_balance": None}
    out["control"] = rm.control_state(db)
    return out

class RiskConfiguration(BaseModel):
    firm: FirmProfile
    limits: InternalLimits


@router.put("/risk/configuration")
def put_risk_configuration(body: RiskConfiguration, db: Session = Depends(get_db),
                           actor: str = Depends(require_owner)):
    """Validate the final pair, then commit both settings in one transaction."""
    errors = cross_validate(body.firm, body.limits)
    if body.firm.id != st.active_firm(db).id:
        errors.append("firm id must match the active profile")
    if errors:
        raise HTTPException(422, {"errors": errors})
    firms = {key: value.model_dump(mode="json") for key, value in st.firm_profiles(db).items()}
    firms[body.firm.id] = body.firm.model_dump(mode="json")
    st._put(db, "firm_profiles", firms, actor)
    st._put(db, "internal_limits", body.limits.model_dump(mode="json"), actor)
    return {"ok": True}


class ResearchPreference(BaseModel):
    profile: str = Field(pattern="^[ABC]$")


@router.get("/research/profile")
def get_research_profile(db: Session = Depends(get_db), _: str = Depends(require_owner)):
    row = db.get(Setting, "research_profile")
    return row.value if row else {"profile": "B"}


@router.put("/research/profile")
def put_research_profile(body: ResearchPreference, db: Session = Depends(get_db),
                         actor: str = Depends(require_owner)):
    st._put(db, "research_profile", body.model_dump(), actor)
    return body
