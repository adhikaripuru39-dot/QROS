"""Commission and bind any active FTMO account dynamically to QROS.

Supports any account capital tier ($5,000, $10,000, $25,000, $50,000, $100,000, $200,000).
Automatically configures percentage-based risk parameters, binds firm account rules,
updates demo test grants with fresh implementation hashes, and verifies audit integrity.
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
from qros.db.models import ControlState, RiskStateRow, Strategy, SystemState
from qros.db.session import session_factory, session_scope
from qros.research.runner import implementation_hash
from qros.services import settings_store as st
from qros.services.account_rules import identity
from qros.services.demo_testing import grant_errors
from qros.services.evidence import canonical_hash
from qros.services.execution import account_key, set_state


def bind_account(
    initial_balance: float = 5000.0,
    server: str = "FTMO-Demo",
    login: int = 1514976566,
    is_demo: bool = True,
    profile_id: str | None = None,
    risk_per_trade_pct: float = 0.60,
    daily_stop_pct: float = 1.80,
    max_open_positions: int = 3,
) -> dict:
    settings = Settings()
    now = datetime.now(timezone.utc)
    
    # 1. Determine or validate profile
    if profile_id is None:
        if initial_balance == 5000.0:
            profile_id = "ftmo_5k_2step"
        elif initial_balance == 50000.0:
            profile_id = "ftmo_free_trial_50k_2step"
        else:
            profile_id = f"ftmo_{int(initial_balance // 1000)}k_2step"

    with session_scope(session_factory(settings.database_url)) as db:
        # Check executor state
        ctrl = db.get(ControlState, 1)
        if ctrl and ctrl.run_state not in ("stopped", "paused_entries"):
            raise RuntimeError("Stop executor before commissioning account binding")

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
            prof = FirmProfile(
                id=profile_id,
                name=f"FTMO 2-Step Evaluation ${int(initial_balance):,}",
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
                daily_reset=DailyReset(timezone="Europe/Prague", time="00:00"),
                profit_target_pct=10.0,
                min_trading_days=4,
                news=NewsRestriction(
                    enabled=True,
                    minutes_before=10,
                    minutes_after=10,
                    flatten_before_news=True,
                    cancel_pending_before_news=True,
                ),
                overnight_allowed=True,
                weekend_allowed=False,
                commission_per_lot_round_turn=7.0,
            )
            st.upsert_firm_profile(db, prof.model_dump(mode="json"), "owner-binding")

        # Activate firm
        firm = st.set_active_firm(db, profile_id, "owner-binding")

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
                    "https://ftmo.com/en/trading-objectives/",
                    "https://ftmo.com/en/faq/can-i-trade-news/",
                ],
                "fee_schedule_verified": False,
                "commission_assumption_round_turn_per_lot": firm.commission_per_lot_round_turn,
                "trial_expiry_verified": False,
                "note": "Dynamic percentage risk model active.",
            },
            now,
        )

        # Set clean risk anchor for the new account
        from qros.services.risk_identity import risk_day_scope
        scope = risk_day_scope(firm.id, dummy_acct, "demo" if is_demo else "live")
        day_str = now.date().isoformat()
        risk_row = db.get(RiskStateRow, 1)
        risk_data = {
            "daily_anchor": firm.initial_balance,
            "daily_limit_amount": firm.initial_balance * 0.05,
            "daily_floor": firm.initial_balance * 0.95,
            "daily_measured": firm.initial_balance,
            "daily_used": 0.0,
            "daily_used_pct_of_limit": 0.0,
            "firm_daily_breached": False,
            "total_base": firm.initial_balance,
            "total_limit_amount": firm.initial_balance * 0.10,
            "total_floor": firm.initial_balance * 0.90,
            "total_measured": firm.initial_balance,
            "total_used": 0.0,
            "total_used_pct_of_limit": 0.0,
            "firm_total_breached": False,
            "internal_measured": firm.initial_balance,
            "internal_daily_warning_floor": firm.initial_balance - (firm.initial_balance * (limits_data["daily_warning_pct"] / 100)),
            "internal_daily_stop_floor": firm.initial_balance - (firm.initial_balance * (limits_data["daily_stop_pct"] / 100)),
            "internal_total_stop_floor": firm.initial_balance - (firm.initial_balance * (limits_data["total_stop_pct"] / 100)),
            "internal_daily_warning": False,
            "internal_daily_stop": False,
            "internal_total_stop": False,
            "effective_floor": firm.initial_balance - (firm.initial_balance * (limits_data["daily_stop_pct"] / 100)),
            "remaining_to_effective_floor": firm.initial_balance * (limits_data["daily_stop_pct"] / 100),
            "halt_required": False,
            "halt_reasons": [],
            "balance": firm.initial_balance,
            "equity": firm.initial_balance,
            "account_key": dummy_key,
            "risk_scope_key": scope,
            "source": "binding_init",
            "currency": firm.currency,
            "initial_balance": firm.initial_balance,
            "sod_balance": firm.initial_balance,
            "sod_equity": firm.initial_balance,
            "anchor_method": "observed_at_reset",
            "open_risk": 0.0,
            "unprotected_tickets": [],
            "currency_exposure": {},
            "limits_version": 1,
            "firm_version": 1,
        }
        if risk_row is None:
            db.add(
                RiskStateRow(
                    id=1,
                    computed_at=now,
                    firm_id=firm.id,
                    trading_day=day_str,
                    data=risk_data,
                    hwm_equity=firm.initial_balance,
                    hwm_eod_balance=firm.initial_balance,
                )
            )
        else:
            risk_row.computed_at = now
            risk_row.firm_id = firm.id
            risk_row.trading_day = day_str
            risk_row.data = risk_data
            risk_row.hwm_equity = firm.initial_balance
            risk_row.hwm_eod_balance = firm.initial_balance

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
        "initial_balance": initial_balance,
        "server": server,
        "login": login,
        "bound_strategies_count": len(bound_strategies),
        "audit_chain_verified": chain["ok"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--balance", type=float, default=5000.0, help="Account initial balance")
    parser.add_argument("--server", default="FTMO-Demo", help="Broker server")
    parser.add_argument("--login", type=int, default=1514976566, help="MT5 login")
    parser.add_argument("--live", action="store_true", help="Bind as live/funded account")
    parser.add_argument("--auto-detect", action="store_true", help="Connect to live MT5 terminal and auto-detect balance & login")
    args = parser.parse_args()

    balance = args.balance
    server = args.server
    login = args.login
    is_demo = not args.live

    if args.auto_detect:
        import MetaTrader5 as mt5
        settings = Settings()
        if not mt5.initialize(path=settings.mt5_path or ""):
            print(f"Warning: MT5 terminal connection failed ({mt5.last_error()}); falling back to args")
        else:
            try:
                a = mt5.account_info()
                if a:
                    server = a.server
                    login = a.login
                    balance = float(a.balance)
                    is_demo = (a.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO)
                    print(f"Auto-detected MT5 Account: {server} | Login: {login} | Balance: ${balance:,.2f} | Demo: {is_demo}")
            finally:
                mt5.shutdown()

    res = bind_account(
        initial_balance=balance,
        server=server,
        login=login,
        is_demo=is_demo,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
