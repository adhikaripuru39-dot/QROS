"""CLI tool to execute single-use out-of-sample (OOS) escrow validation.

Generates cryptographic evidence reports with verified broker specs and execution costs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

# Ensure backend is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from qros.config.settings import get_settings
from qros.db.models import Strategy, EvidenceReport
from qros.db.session import session_factory, session_scope
from qros.services.research_worker import ResearchWorker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy-id", type=str, required=True, help="Strategy ID to validate")
    parser.add_argument("--days", type=int, default=180, help="Lookback window in days")
    parser.add_argument("--max-bars", type=int, default=15000, help="Max bars to load")
    parser.add_argument("--profile", type=str, default="B", choices=["A", "B", "C"], help="Selection profile")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without consuming OOS escrow")
    args = parser.parse_args()

    settings = get_settings()
    factory = session_factory(settings.database_url)

    with session_scope(factory) as db:
        strat = db.get(Strategy, args.strategy_id)
        if strat is None:
            sys.exit(f"Strategy {args.strategy_id} not found in database.")
        
        runtime = strat.spec.get("runtime", {})
        symbol = runtime.get("symbol")
        timeframe = runtime.get("timeframe", "M15")
        timeframe_seconds = runtime.get("timeframe_seconds", 900)
        hypothesis = strat.hypothesis_id

        print(f"Validating Strategy: {strat.id}")
        print(f"Hypothesis: {hypothesis} | Symbol: {symbol} | Timeframe: {timeframe} ({timeframe_seconds}s)")
        print(f"Runtime Exit Rules: Stop={runtime.get('stop_atr_multiple', 2.0)} ATR | Target={runtime.get('target_atr_multiple', 3.0)} ATR")
        print(f"Account Basis: Dynamically scaled from active firm balance")

    if args.dry_run:
        print("[DRY RUN] OOS Escrow will not be consumed.")
        return 0

    worker = ResearchWorker(settings, factory, max_bars=args.max_bars)
    payload = {
        "strategy_id": args.strategy_id,
        "runtime_spec": runtime,
        "symbol": symbol,
        "timeframe": timeframe,
        "days": args.days,
        "candidate_ids": [hypothesis],
        "verify_broker_specs": True,
        "verify_execution_costs": True,
        "verify_runtime_equivalence": True,
        "review_independent_trades": True,
        "finalize_oos": True,
        "allow_finalize_oos": True,
    }

    job_id = f"oos_val_{args.strategy_id}"
    print(f"\nExecuting research pipeline & OOS evaluation...")
    try:
        result = worker.process(job_id, payload)
        print("\n" + "=" * 60)
        print("VALIDATION PROTOCOL RESULT")
        print("=" * 60)
        print(f"Dataset Version   : {result.get('dataset_version')}")
        print(f"Selected Rows     : {result.get('rows')} bars")
        print(f"OOS Evaluated     : {result.get('oos_evaluated')}")
        print(f"Passed Protocol   : {result.get('eligible')}")
        print(f"Report Path       : {result.get('report_path')}")
        print(f"Report Hash       : {result.get('report_hash')}")
        
        with session_scope(factory) as db:
            rep = db.query(EvidenceReport).filter_by(strategy_id=args.strategy_id).order_by(EvidenceReport.created_at.desc()).first()
            if rep:
                print(f"Evidence Report ID: {rep.id} (passed={rep.passed})")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"Validation failed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

