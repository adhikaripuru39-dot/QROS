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
from qros.config.settings import Settings
from qros.db.models import ControlState, Instrument, RiskStateRow, Strategy, SystemState
from qros.db.session import session_factory, session_scope
from qros.research.runner import implementation_hash
from qros.services import settings_store as st
from qros.services.account_rules import identity
from qros.services.evidence import canonical_hash
from qros.services.execution import account_key, set_state

ACTIVE_FIVE_SYMBOLS = {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCAD"}

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
    login: int = 1514976566,
    is_demo: bool = True,
    firm_brand: str = "fundednext",
    profile_id: str | None = None,
    risk_per_trade_pct: float = 0.60,
    daily_stop_pct: float = 1.80,
    max_open_positions: int = 3,
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

        # Ensure only the 5 core instruments are enabled in the active DB
        for inst in db.execute(select(Instrument)).scalars():
            inst.enabled = inst.symbol in ACTIVE_FIVE_SYMBOLS

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

        db.flush()

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
        "server": server,
        "login": login,
        "bound_strategies_count": len(bound_strategies),
        "audit_chain_verified": chain["ok"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--balance", type=float, default=5000.0, help="Account initial balance (e.g. 5000, 6000, 15000, 50000)")
    parser.add_argument("--firm", choices=["fundednext", "ftmo"], default="fundednext", help="Prop firm brand")
    parser.add_argument("--server", default=None, help="Broker server name (auto-detected if MT5 is running)")
    parser.add_argument("--login", type=int, default=None, help="MT5 login number (auto-detected if MT5 is running)")
    parser.add_argument("--live", action="store_true", help="Bind as live/funded account")
    parser.add_argument("--auto-detect", action="store_true", default=True, help="Auto-detect server, login, and balance from running MT5")
    parser.add_argument("--no-auto-detect", dest="auto_detect", action="store_false", help="Disable MT5 auto-detection")
    args = parser.parse_args()

    balance = args.balance
    firm_brand = args.firm
    server = args.server or ("FundedNext-Server" if firm_brand == "fundednext" else "FTMO-Demo")
    login = args.login or 1514976566
    is_demo = not args.live

    if args.auto_detect:
        try:
            import MetaTrader5 as mt5
            settings = Settings()
            init_ok = mt5.initialize(path=settings.mt5_path) if settings.mt5_path else mt5.initialize()
            if init_ok:
                try:
                    a = mt5.account_info()
                    if a:
                        server = a.server
                        login = a.login
                        if args.balance == 5000.0 and a.balance > 0:
                            # Round to nearest 1,000 tier for initial balance anchor
                            balance = float(round(a.balance / 1000.0) * 1000.0) or float(a.balance)
                        is_demo = (a.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO)
                        print(f"Auto-detected MT5 Account: Server={server} | Login={login} | Balance=${balance:,.2f} | Demo={is_demo}")
                        for sym in ACTIVE_FIVE_SYMBOLS:
                            mt5.symbol_select(sym, True)
                finally:
                    mt5.shutdown()
        except Exception as exc:
            print(f"Note: MT5 auto-detect skipped ({exc}); using supplied arguments.")

    res = bind_account(
        initial_balance=balance,
        server=server,
        login=login,
        is_demo=is_demo,
        firm_brand=firm_brand,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
