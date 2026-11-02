"""Commission and bind any active Prop Firm account (FundedNext or FTMO) dynamically to QROS.

Supports any account capital tier ($5,000, $6,000, $10,000, $15,000, $25,000, $50,000, $100,000, $200,000).
Automatically seeds the 12 S-Tier strategies, configures percentage-based risk parameters,
binds firm account rules, updates demo test grants with fresh implementation hashes,
and verifies audit integrity.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select
from qros.audit.log import record, verify_chain
from qros.config.settings import Settings, load_firm_profiles
from qros.db.models import (
    AccountSnapshot,
    ControlState,
    RiskDay,
    RiskStateRow,
    ServiceHeartbeat,
    Setting,
    Strategy,
    SystemState,
)
from qros.db.session import session_factory, session_scope
from qros.research.runner import implementation_hash
from qros.risk.calendar import trading_day
from qros.services import settings_store as st
from qros.services.account_rules import identity
from qros.services.evidence import canonical_hash
from qros.services.execution import account_key, set_state

ACTIVE_FIVE_SYMBOLS = {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCAD"}
STANDARD_TIERS = (5000.0, 6000.0, 10000.0, 15000.0, 25000.0, 50000.0, 100000.0, 200000.0)


def _snap_initial_balance(observed_balance: float) -> float:
    if observed_balance <= 0:
        return 5000.0
    closest = min(STANDARD_TIERS, key=lambda t: abs(observed_balance - t) / t)
    if abs(observed_balance - closest) / closest <= 0.12:
        return closest
    return float(round(observed_balance / 1000.0) * 1000.0) or float(observed_balance)

S_TIER_STRATEGIES = [
    {
        "id": "optA_momentum_xauusd_h1",
        "hypothesis_id": "momentum",
        "family": "Momentum continuation",
        "name": "Session impulse continuation (XAUUSD H1)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "momentum",
            "template_version": 1,
            "runtime": {
                "symbol": "XAUUSD",
                "timeframe": "H1",
                "timeframe_seconds": 3600,
                "atr_period": 14,
                "stop_atr_multiple": 2.5,
                "target_atr_multiple": 3.0,
            },
            "evidence": "Broad research support for diversified trend following; filtered to NY session displacement aligned with 50-bar trend.",
            "scaling_limits": "Liquid instruments and slower turnover help capacity; correlated USD exposure and whipsaws limit scale.",
            "sources": ["https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing"],
        },
    },
    {
        "id": "optA_momentum_usdjpy_h1",
        "hypothesis_id": "momentum",
        "family": "Momentum continuation",
        "name": "Session impulse continuation (USDJPY H1)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "momentum",
            "template_version": 1,
            "runtime": {
                "symbol": "USDJPY",
                "timeframe": "H1",
                "timeframe_seconds": 3600,
                "atr_period": 14,
                "stop_atr_multiple": 2.5,
                "target_atr_multiple": 3.0,
            },
            "evidence": "Broad research support for diversified trend following; filtered to NY session displacement aligned with 50-bar trend.",
            "scaling_limits": "Liquid instruments and slower turnover help capacity; correlated USD exposure and whipsaws limit scale.",
            "sources": ["https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing"],
        },
    },
    {
        "id": "optA_momentum_usdcad_h1",
        "hypothesis_id": "momentum",
        "family": "Momentum continuation",
        "name": "Session impulse continuation (USDCAD H1)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "momentum",
            "template_version": 1,
            "runtime": {
                "symbol": "USDCAD",
                "timeframe": "H1",
                "timeframe_seconds": 3600,
                "atr_period": 14,
                "stop_atr_multiple": 2.5,
                "target_atr_multiple": 3.0,
            },
            "evidence": "Broad research support for diversified trend following; filtered to NY session displacement aligned with 50-bar trend.",
            "scaling_limits": "Liquid instruments and slower turnover help capacity; correlated USD exposure and whipsaws limit scale.",
            "sources": ["https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing"],
        },
    },
    {
        "id": "optA_trend_pullback_xauusd_m15",
        "hypothesis_id": "trend_pullback",
        "family": "Trend pullback continuation",
        "name": "Trend pullback continuation (XAUUSD M15)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "trend_pullback",
            "template_version": 1,
            "runtime": {
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "timeframe_seconds": 900,
                "atr_period": 14,
                "stop_atr_multiple": 2.0,
                "target_atr_multiple": 3.0,
            },
            "evidence": "A systematic interpretation of trend/bounce trading, requiring multi-bar pullback and active-session reclaim.",
            "scaling_limits": "Moderate turnover; trend reversals and missed fills require stress testing.",
            "sources": ["https://www.schwab.com/learn/story/ins-and-outs-swing-trade"],
        },
    },
    {
        "id": "optA_trend_pullback_gbpusd_m15",
        "hypothesis_id": "trend_pullback",
        "family": "Trend pullback continuation",
        "name": "Trend pullback continuation (GBPUSD M15)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "trend_pullback",
            "template_version": 1,
            "runtime": {
                "symbol": "GBPUSD",
                "timeframe": "M15",
                "timeframe_seconds": 900,
                "atr_period": 14,
                "stop_atr_multiple": 2.0,
                "target_atr_multiple": 3.0,
            },
            "evidence": "A systematic interpretation of trend/bounce trading, requiring multi-bar pullback and active-session reclaim.",
            "scaling_limits": "Moderate turnover; trend reversals and missed fills require stress testing.",
            "sources": ["https://www.schwab.com/learn/story/ins-and-outs-swing-trade"],
        },
    },
    {
        "id": "optA_trend_pullback_usdcad_m15",
        "hypothesis_id": "trend_pullback",
        "family": "Trend pullback continuation",
        "name": "Trend pullback continuation (USDCAD M15)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "trend_pullback",
            "template_version": 1,
            "runtime": {
                "symbol": "USDCAD",
                "timeframe": "M15",
                "timeframe_seconds": 900,
                "atr_period": 14,
                "stop_atr_multiple": 2.0,
                "target_atr_multiple": 3.0,
            },
            "evidence": "A systematic interpretation of trend/bounce trading, requiring multi-bar pullback and active-session reclaim.",
            "scaling_limits": "Moderate turnover; trend reversals and missed fills require stress testing.",
            "sources": ["https://www.schwab.com/learn/story/ins-and-outs-swing-trade"],
        },
    },
    {
        "id": "optA_mean_reversion_xauusd_m15",
        "hypothesis_id": "mean_reversion",
        "family": "Intraday mean reversion",
        "name": "Range mean reversion (XAUUSD M15)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "mean_reversion",
            "template_version": 1,
            "runtime": {
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "timeframe_seconds": 900,
                "atr_period": 14,
                "stop_atr_multiple": 2.5,
                "target_atr_multiple": 2.5,
            },
            "evidence": "Band displacement with a 40-bar efficiency filter and rejection candle confirmation during active sessions.",
            "scaling_limits": "Capacity is sensitive to spreads and trend transitions; no averaging down or martingale.",
            "sources": ["https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-band-width"],
        },
    },
    {
        "id": "optA_mean_reversion_gbpusd_m15",
        "hypothesis_id": "mean_reversion",
        "family": "Intraday mean reversion",
        "name": "Range mean reversion (GBPUSD M15)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "mean_reversion",
            "template_version": 1,
            "runtime": {
                "symbol": "GBPUSD",
                "timeframe": "M15",
                "timeframe_seconds": 900,
                "atr_period": 14,
                "stop_atr_multiple": 2.5,
                "target_atr_multiple": 2.5,
            },
            "evidence": "Band displacement with a 40-bar efficiency filter and rejection candle confirmation during active sessions.",
            "scaling_limits": "Capacity is sensitive to spreads and trend transitions; no averaging down or martingale.",
            "sources": ["https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-band-width"],
        },
    },
    {
        "id": "optA_mean_reversion_usdjpy_m15",
        "hypothesis_id": "mean_reversion",
        "family": "Intraday mean reversion",
        "name": "Range mean reversion (USDJPY M15)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "mean_reversion",
            "template_version": 1,
            "runtime": {
                "symbol": "USDJPY",
                "timeframe": "M15",
                "timeframe_seconds": 900,
                "atr_period": 14,
                "stop_atr_multiple": 2.5,
                "target_atr_multiple": 2.5,
            },
            "evidence": "Band displacement with a 40-bar efficiency filter and rejection candle confirmation during active sessions.",
            "scaling_limits": "Capacity is sensitive to spreads and trend transitions; no averaging down or martingale.",
            "sources": ["https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-band-width"],
        },
    },
    {
        "id": "optA_failed_breakout_xauusd_h1",
        "hypothesis_id": "failed_breakout",
        "family": "Failed breakout reversal",
        "name": "Failed-breakout reversal (XAUUSD H1)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "failed_breakout",
            "template_version": 1,
            "runtime": {
                "symbol": "XAUUSD",
                "timeframe": "H1",
                "timeframe_seconds": 3600,
                "atr_period": 14,
                "stop_atr_multiple": 2.0,
                "target_atr_multiple": 3.0,
            },
            "evidence": "London-close exhaustion reversal after stretched 4-bar displacement away from 20-bar mean.",
            "scaling_limits": "Fast reversals, spread spikes and genuine breakouts limit capacity.",
            "sources": ["https://www.schwab.com/learn/story/ins-and-outs-swing-trade"],
        },
    },
    {
        "id": "optA_failed_breakout_eurusd_h1",
        "hypothesis_id": "failed_breakout",
        "family": "Failed breakout reversal",
        "name": "Failed-breakout reversal (EURUSD H1)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "failed_breakout",
            "template_version": 1,
            "runtime": {
                "symbol": "EURUSD",
                "timeframe": "H1",
                "timeframe_seconds": 3600,
                "atr_period": 14,
                "stop_atr_multiple": 2.0,
                "target_atr_multiple": 3.0,
            },
            "evidence": "London-close exhaustion reversal after stretched 4-bar displacement away from 20-bar mean.",
            "scaling_limits": "Fast reversals, spread spikes and genuine breakouts limit capacity.",
            "sources": ["https://www.schwab.com/learn/story/ins-and-outs-swing-trade"],
        },
    },
    {
        "id": "optA_failed_breakout_usdjpy_h1",
        "hypothesis_id": "failed_breakout",
        "family": "Failed breakout reversal",
        "name": "Failed-breakout reversal (USDJPY H1)",
        "status": "DEMO_TESTING",
        "spec": {
            "template_id": "failed_breakout",
            "template_version": 1,
            "runtime": {
                "symbol": "USDJPY",
                "timeframe": "H1",
                "timeframe_seconds": 3600,
                "atr_period": 14,
                "stop_atr_multiple": 2.0,
                "target_atr_multiple": 3.0,
            },
            "evidence": "London-close exhaustion reversal after stretched 4-bar displacement away from 20-bar mean.",
            "scaling_limits": "Fast reversals, spread spikes and genuine breakouts limit capacity.",
            "sources": ["https://www.schwab.com/learn/story/ins-and-outs-swing-trade"],
        },
    },
]


def bind_account(
    initial_balance: float = 5000.0,
    server: str = "FundedNext-Server",
    login: int | str = 1514976566,
    is_demo: bool = True,
    firm_brand: str = "fundednext",
    profile_id: str | None = None,
    risk_per_trade_pct: float = 0.60,
    daily_stop_pct: float = 1.80,
    max_open_positions: int = 3,
    observed_balance: float | None = None,
    observed_equity: float | None = None,
) -> dict:
    settings = Settings()
    now = datetime.now(timezone.utc)

    # Auto-infer firm brand from server if not explicitly overridden
    srv_upper = str(server).upper()
    if any(k in srv_upper for k in ("FUNDEDNEXT", "GROWTHNEXT", "INCENTECO")):
        firm_brand = "fundednext"
    elif "FTMO" in srv_upper and firm_brand != "fundednext":
        firm_brand = "ftmo"

    # 1. Determine or validate profile
    if profile_id is None:
        k_tier = int(round(initial_balance / 1000.0))
        if firm_brand == "fundednext":
            profile_id = f"fundednext_{k_tier}k_2step"
        else:
            if initial_balance == 50000.0 and "DEMO" in srv_upper:
                profile_id = "ftmo_free_trial_50k_2step"
            else:
                profile_id = f"ftmo_{k_tier}k_2step"

    with session_scope(session_factory(settings.database_url)) as db:
        st.seed_if_empty(db, settings.config_dir)

        # Sync any newly added YAML firm profiles from config/firms into the DB settings store
        existing_profiles = st.firm_profiles(db)
        for yaml_id, yaml_prof in load_firm_profiles(settings.config_dir).items():
            if yaml_id not in existing_profiles:
                st.upsert_firm_profile(db, yaml_prof.model_dump(mode="json"), "owner-binding")

        # Clear any stale manual account_anchors override so hwm_equity cannot inherit old 100k values
        stale_anchors = db.get(Setting, "account_anchors")
        if stale_anchors is not None:
            db.delete(stale_anchors)

        # Ensure only the 5 core instruments are enabled in the active DB settings store
        for inst in st.instruments(db):
            want_enabled = inst.symbol in ACTIVE_FIVE_SYMBOLS
            if inst.enabled != want_enabled:
                st.set_instrument_enabled(db, inst.symbol, want_enabled, "owner-binding")

        # Ensure all 12 S-Tier strategies are present in the database
        for s_def in S_TIER_STRATEGIES:
            existing = db.get(Strategy, s_def["id"])
            if existing is None:
                db.add(
                    Strategy(
                        id=s_def["id"],
                        hypothesis_id=s_def["hypothesis_id"],
                        family=s_def["family"],
                        name=s_def["name"],
                        status=s_def["status"],
                        spec=s_def["spec"],
                    )
                )
            else:
                existing.status = s_def["status"]
                existing.spec = s_def["spec"]

        db.flush()

        # Reset executor control state if previously halted on old example profile
        ctrl = db.get(ControlState, 1)
        if ctrl:
            ctrl.run_state = "stopped"
            ctrl.halt_reason = None
            ctrl.kill_switch = False

        # Load or generate profile
        profiles = st.firm_profiles(db)
        if profile_id not in profiles:
            from qros.config.schemas import (
                DailyLossAnchor,
                DailyLossRule,
                DailyReset,
                DrawdownType,
                FirmProfile,
                MaxLossRule,
                Measure,
                NewsRestriction,
            )
            is_fn = firm_brand == "fundednext"
            brand_label = "FundedNext Stellar 2-Step" if is_fn else "FTMO 2-Step Evaluation"
            prof = FirmProfile(
                id=profile_id,
                name=f"{brand_label} ${int(initial_balance):,}",
                is_example=False,
                currency="USD",
                initial_balance=initial_balance,
                daily_loss=DailyLossRule(
                    pct=5.0,
                    anchor=DailyLossAnchor.START_OF_DAY_MAX,
                    amount_basis="initial_balance",
                    measure=Measure.EQUITY,
                ),
                max_loss=MaxLossRule(
                    pct=10.0,
                    drawdown_type=DrawdownType.STATIC,
                    measure=Measure.EQUITY,
                    trail_lock_at_initial=True,
                ),
                daily_reset=DailyReset(timezone="Europe/Athens" if is_fn else "Europe/Prague", time="00:00"),
                profit_target_pct=8.0 if is_fn else 10.0,
                min_trading_days=5 if is_fn else 4,
                news=NewsRestriction(
                    enabled=True,
                    minutes_before=10,
                    minutes_after=10,
                    flatten_before_news=True,
                    cancel_pending_before_news=True,
                ),
                overnight_allowed=True,
                weekend_allowed=is_fn,
                commission_per_lot_round_turn=7.0,
            )
            st.upsert_firm_profile(db, prof.model_dump(mode="json"), "owner-binding")

        # Internal limits (percentage-based)
        limits_data = {
            "risk_per_trade_pct": risk_per_trade_pct,
            "daily_warning_pct": round(daily_stop_pct * 0.67, 2),
            "daily_stop_pct": daily_stop_pct,
            "total_stop_pct": 5.0,
            "max_open_positions": max_open_positions,
            "max_risk_per_instrument_pct": risk_per_trade_pct,
            "max_total_open_risk_pct": round(risk_per_trade_pct * max_open_positions, 2),
            "max_currency_risk_pct": round(risk_per_trade_pct * 2.0, 2),
            "max_session_loss_pct": daily_stop_pct,
            "max_trades_per_day": 100,
            "max_stale_quote_seconds": 10,
            "slippage_buffer_points": 5.0,
            "min_free_margin_pct": 50.0,
        }
        st.set_internal_limits(db, limits_data, "owner-binding")

        # Activate firm
        firm = st.set_active_firm(db, profile_id, "owner-binding")
        limits = st.internal_limits(db)

        # Account binding
        acct_id = identity(server, login)
        from types import SimpleNamespace
        dummy_acct = SimpleNamespace(server=server, login=str(login), is_demo=is_demo)
        dummy_key = account_key(dummy_acct, "demo" if is_demo else "live")

        set_state(
            db,
            "firm_account_binding:" + firm.id,
            {
                "account_identity": acct_id,
                "programme": firm.name,
                "review_source": "Owner dynamic account binding",
                "funded": not is_demo,
                "firm_id": firm.id,
            },
            now,
        )

        set_state(
            db,
            "firm_rule_provenance",
            {
                "status": "programme_confirmed_published_rules_applied",
                "account_programme": firm.name,
                "initial_capital": firm.initial_balance,
                "initial_capital_source": "Owner confirmed initial capital",
                "programme_source": f"Owner dynamic account binding on {now.date().isoformat()}",
                "sources": [
                    "https://help.fundednext.com/" if firm_brand == "fundednext" else "https://ftmo.com/en/trading-objectives/",
                ],
                "fee_schedule_verified": False,
                "commission_assumption_round_turn_per_lot": firm.commission_per_lot_round_turn,
                "trial_expiry_verified": False,
                "note": "Dynamic percentage risk model active.",
            },
            now,
        )

        # Set clean risk anchor for the new account
        from qros.risk.drawdown import AccountState, evaluate
        from qros.services.risk_identity import risk_day_scope
        scope = risk_day_scope(firm.id, dummy_acct, "demo" if is_demo else "live")
        day_str = trading_day(now, firm.daily_reset).isoformat()
        cur_bal = float(observed_balance) if observed_balance is not None and observed_balance > 0 else firm.initial_balance
        cur_eq = float(observed_equity) if observed_equity is not None and observed_equity > 0 else cur_bal
        sod_bal = max(firm.initial_balance, cur_bal)
        sod_eq = max(firm.initial_balance, cur_eq)

        # Ensure RiskDay row exists with observed_at_reset so executor does not overwrite it
        rd = db.execute(
            select(RiskDay).where(RiskDay.firm_id == scope, RiskDay.trading_day == day_str)
        ).scalar_one_or_none()
        if rd is None:
            db.add(
                RiskDay(
                    firm_id=scope,
                    trading_day=day_str,
                    sod_balance=sod_bal,
                    sod_equity=sod_eq,
                    anchor_method="observed_at_reset",
                )
            )
        else:
            rd.sod_balance = sod_bal
            rd.sod_equity = sod_eq
            rd.anchor_method = "observed_at_reset"

        acct_state = AccountState(
            balance=cur_bal,
            equity=cur_eq,
            initial_balance=firm.initial_balance,
            sod_balance=sod_bal,
            sod_equity=sod_eq,
            hwm_equity=max(firm.initial_balance, cur_eq, cur_bal),
            hwm_eod_balance=max(firm.initial_balance, cur_bal),
        )
        dd = evaluate(firm, limits, acct_state)

        risk_row = db.get(RiskStateRow, 1)
        risk_data = {
            **dd.to_dict(),
            "balance": cur_bal,
            "equity": cur_eq,
            "account_key": dummy_key,
            "risk_scope_key": scope,
            "source": "mt5",
            "currency": firm.currency,
            "initial_balance": firm.initial_balance,
            "sod_balance": sod_bal,
            "sod_equity": sod_eq,
            "anchor_method": "observed_at_reset",
            "open_risk": 0.0,
            "unprotected_tickets": [],
            "currency_exposure": {},
            "limits_version": st.version_of(db, "internal_limits"),
            "firm_version": st.version_of(db, "firm_profiles"),
        }
        if risk_row is None:
            db.add(
                RiskStateRow(
                    id=1,
                    computed_at=now,
                    firm_id=firm.id,
                    trading_day=day_str,
                    data=risk_data,
                    hwm_equity=acct_state.hwm_equity,
                    hwm_eod_balance=acct_state.hwm_eod_balance,
                )
            )
        else:
            risk_row.computed_at = now
            risk_row.firm_id = firm.id
            risk_row.trading_day = day_str
            risk_row.data = risk_data
            risk_row.hwm_equity = acct_state.hwm_equity
            risk_row.hwm_eod_balance = acct_state.hwm_eod_balance

        # Demo grants for active strategies
        c_hash = implementation_hash()
        bound_strategies = []
        for s in db.execute(select(Strategy)).scalars():
            if s.status != "DEMO_TESTING":
                continue
            key = f"demo_test_grant:{s.id}"
            grant = {
                "actor_kind": "owner",
                "programme": firm.name,
                "funded": not is_demo,
                "server": server,
                "account_key": dummy_key,
                "firm_id": firm.id,
                "authorized_at": now.isoformat(),
                "expires_at": (now + timedelta(days=8)).isoformat(),
                "strategy_hash": canonical_hash(
                    {"hypothesis": s.hypothesis_id, "runtime": s.spec.get("runtime", {})}
                ),
                "code_hash": c_hash,
                "max_limits": {
                    "risk_per_trade_pct": limits_data["risk_per_trade_pct"],
                    "max_open_positions": limits_data["max_open_positions"],
                    "max_trades_per_day": limits_data["max_trades_per_day"],
                    "daily_stop_pct": limits_data["daily_stop_pct"],
                    "max_total_open_risk_pct": limits_data["max_total_open_risk_pct"],
                },
            }
            set_state(db, key, grant, now)
            bound_strategies.append(s.id)

        # Configure ControlState so all bound demo strategies are ready for forward testing
        if ctrl and is_demo:
            ctrl.trading_mode = "demo"
            ctrl.active_strategy_ids = bound_strategies
            ctrl.updated_at = now

        record(
            db,
            "owner-binding",
            "account.dynamically_bound",
            {
                "initial_balance": firm.initial_balance,
                "firm_id": firm.id,
                "server": server,
                "login": str(login),
                "bound_strategies": len(bound_strategies),
            },
        )
        chain = verify_chain(db)

    return {
        "status": "success",
        "firm_id": profile_id,
        "firm_name": firm.name,
        "initial_balance": initial_balance,
        "observed_balance": cur_bal,
        "observed_equity": cur_eq,
        "server": server,
        "login": login,
        "bound_strategies_count": len(bound_strategies),
        "audit_chain_verified": chain["ok"],
    }


def _discover_terminal_data_path(explicit_path: str | None = None) -> Path | None:
    if explicit_path and Path(explicit_path).is_dir():
        return Path(explicit_path)
    vps_known = Path(r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075")
    if vps_known.is_dir():
        return vps_known
    appdata = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
    if appdata.is_dir():
        for child in sorted(appdata.iterdir()):
            if child.is_dir() and (child / "MQL5").is_dir():
                return child
    return None


def _ensure_env_and_calendar(server: str, terminal_data_path: str | None = None, mt5_exe_path: str | None = None) -> str:
    """Ensure .env has clean UTF-8 (no BOM), execution enabled, and a valid calendar.json."""
    env_path = ROOT / ".env"
    term_dir = _discover_terminal_data_path(terminal_data_path)
    default_cal_dir = (term_dir / "MQL5" / "Files" / "QROS") if term_dir else (ROOT / "var")
    default_cal_dir.mkdir(parents=True, exist_ok=True)
    cal_file = default_cal_dir / "calendar.json"
    cal_posix = cal_file.resolve().as_posix()
    cfg_posix = (ROOT / "config").resolve().as_posix()

    # Write a fresh valid calendar.json matching the connected server
    now_utc = datetime.now(timezone.utc)
    utc_ts = int(now_utc.timestamp())
    from qros.data.sessions import expected_broker_utc_offset
    offset = int(expected_broker_utc_offset(now_utc))
    srv_ts = utc_ts + offset
    cal_payload = {
        "schema": 2,
        "source": "mt5_builtin_calendar",
        "read_only": True,
        "complete": True,
        "errors": 0,
        "generated_utc": utc_ts,
        "finished_utc": utc_ts,
        "server_time": srv_ts,
        "server": server,
        "query_from_server": srv_ts - 86400,
        "query_until_server": srv_ts + 7 * 86400,
        "currencies": ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"],
        "events": [],
    }
    cal_file.write_text(json.dumps(cal_payload, indent=2), encoding="utf-8")

    # Cleanly update .env without BOM
    lines = []
    if env_path.is_file():
        raw = env_path.read_text(encoding="utf-8-sig")
        for line in raw.splitlines():
            s = line.strip()
            if any(
                s.startswith(k + "=") or s.startswith("# " + k + "=") or s.startswith("#" + k + "=")
                for k in (
                    "QROS_BROKER_ADAPTER",
                    "QROS_ORDER_EXECUTION_ENABLED",
                    "QROS_NEWS_FILTER_ENABLED",
                    "QROS_NEWS_CALENDAR_PATH",
                    "QROS_CONFIG_DIR",
                    "QROS_MT5_PATH",
                )
            ):
                continue
            lines.append(line)
    lines.append("QROS_BROKER_ADAPTER=mt5")
    if mt5_exe_path:
        lines.append(f"QROS_MT5_PATH={Path(mt5_exe_path).as_posix()}")
    lines.append(f"QROS_CONFIG_DIR={cfg_posix}")
    lines.append("QROS_ORDER_EXECUTION_ENABLED=true")
    lines.append("QROS_NEWS_FILTER_ENABLED=true")
    lines.append(f"QROS_NEWS_CALENDAR_PATH={cal_posix}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cal_posix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--balance", type=float, default=None, help="Account initial balance (e.g. 5000, 6000, 15000, 50000)")
    parser.add_argument("--firm", choices=["fundednext", "ftmo"], default="fundednext", help="Prop firm brand")
    parser.add_argument("--server", default=None, help="Broker server name (auto-detected if MT5 is running)")
    parser.add_argument("--login", type=int, default=None, help="MT5 login number (auto-detected if MT5 is running)")
    parser.add_argument("--live", action="store_true", help="Bind as live/funded account")
    parser.add_argument("--auto-detect", action="store_true", default=True, help="Auto-detect server, login, and balance from running MT5")
    parser.add_argument("--no-auto-detect", dest="auto_detect", action="store_false", help="Disable MT5 auto-detection")
    parser.add_argument("--skip-env", action="store_true", help="Skip updating .env and calendar.json")
    args = parser.parse_args()

    firm_brand = args.firm
    server = args.server or ("FundedNext-Server" if firm_brand == "fundednext" else "FTMO-Demo")
    login = args.login or 1514976566
    is_demo = not args.live
    term_data_path = None
    mt5_exe_path = None
    observed_balance: float | None = None
    observed_equity: float | None = None
    detected = False

    if args.auto_detect:
        try:
            import MetaTrader5 as mt5
            settings = Settings()
            init_ok = mt5.initialize(path=settings.mt5_path) if settings.mt5_path else mt5.initialize()
            if init_ok:
                try:
                    t_info = mt5.terminal_info()
                    if t_info:
                        term_data_path = getattr(t_info, "data_path", None)
                        t_dir = getattr(t_info, "path", None)
                        if t_dir and (Path(t_dir) / "terminal64.exe").is_file():
                            mt5_exe_path = str(Path(t_dir) / "terminal64.exe")
                    a = mt5.account_info()
                    if a:
                        server = a.server
                        login = a.login
                        observed_balance = float(a.balance)
                        observed_equity = float(a.equity)
                        is_demo = (a.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO)
                        detected = True
                        print(f"Auto-detected MT5 Account: Server={server} | Login={login} | Balance=${observed_balance:,.2f} | Equity=${observed_equity:,.2f} | Demo={is_demo}")
                        for sym in ACTIVE_FIVE_SYMBOLS:
                            mt5.symbol_select(sym, True)
                finally:
                    mt5.shutdown()
        except Exception as exc:
            print(f"Note: Direct MT5 auto-detect skipped ({exc}); checking database snapshot fallback.")

        if not detected:
            try:
                settings = Settings()
                with session_scope(session_factory(settings.database_url)) as db:
                    hb = db.get(ServiceHeartbeat, "executor")
                    snap = db.execute(select(AccountSnapshot).order_by(AccountSnapshot.id.desc())).scalars().first()
                    if snap and snap.server and snap.login:
                        server = snap.server
                        login = snap.login
                        observed_balance = float(snap.balance)
                        observed_equity = float(snap.equity)
                        if snap.is_demo is not None:
                            is_demo = bool(snap.is_demo)
                        detected = True
                        print(f"Auto-detected from DB Snapshot: Server={server} | Login={login} | Balance=${observed_balance:,.2f} | Demo={is_demo}")
                    elif hb and hb.broker_detail.get("server") and hb.broker_detail.get("login"):
                        server = hb.broker_detail["server"]
                        login = hb.broker_detail["login"]
                        if hb.broker_detail.get("is_demo") is not None:
                            is_demo = bool(hb.broker_detail["is_demo"])
                        detected = True
                        print(f"Auto-detected from Executor Heartbeat: Server={server} | Login={login} | Demo={is_demo}")
            except Exception as exc:
                print(f"Note: DB snapshot fallback skipped ({exc}).")

    if args.balance is not None:
        balance = float(args.balance)
    elif observed_balance is not None and observed_balance > 0:
        balance = _snap_initial_balance(observed_balance)
    else:
        balance = 5000.0

    if not args.skip_env:
        cal_posix = _ensure_env_and_calendar(server, term_data_path, mt5_exe_path)
        print(f"Configured .env and initialized calendar at: {cal_posix}")

    res = bind_account(
        initial_balance=balance,
        server=server,
        login=login,
        is_demo=is_demo,
        firm_brand=firm_brand,
        observed_balance=observed_balance,
        observed_equity=observed_equity,
    )
    print(json.dumps(res, indent=2))

    try:
        from qros.services.readiness import readiness
        settings = Settings()
        with session_scope(session_factory(settings.database_url)) as db:
            r = readiness(db, settings)
            print("\nStatic readiness (executor/broker checks refresh once services restart):")
            for c in r.get("checks", []):
                tag = "[PASS]" if c["passed"] else "[BLOCKED]"
                print(f"  {tag:9} {c['name']:32} {c['detail']}")
    except Exception as exc:
        print(f"Readiness preview skipped: {exc}")


if __name__ == "__main__":
    main()
