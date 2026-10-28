"""Read-only automated MT5 history synchronization (no order API calls)."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
from .history import HistoryStore, TIMEFRAMES, _utc


def sync_history(mt5, root, symbols, start, end, timeframes=tuple(TIMEFRAMES), *, include_ticks=False,
                 timestamp_metadata=None,request_axis_offset_seconds=0):
    """Caller owns terminal connection. Every sync creates new immutable versions.

    Failures are returned individually; quality and market closures are never
    silently approved. The report is append-only by unique filename.
    """
    store=HistoryStore(root)
    start=_utc(start)+timedelta(seconds=request_axis_offset_seconds)
    end=_utc(end)+timedelta(seconds=request_axis_offset_seconds)
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"datasets":[],"errors":[],"ticks":[]}
    for symbol in symbols:
        spec=mt5.symbol_info(symbol)
        if spec is None:
            report["errors"].append({"symbol":symbol,"error":"symbol_info unavailable"}); continue
        mode=getattr(spec,"chart_mode",None)
        basis="bid" if mode==getattr(mt5,"SYMBOL_CHART_MODE_BID",0) else "last" if mode==getattr(mt5,"SYMBOL_CHART_MODE_LAST",1) else None
        if basis is None:
            report["errors"].append({"symbol":symbol,"error":"unknown chart price basis"}); continue
        for timeframe in timeframes:
            try:
                seconds=TIMEFRAMES[timeframe]
                # Request completed UTC-grid intervals only; broker calendar remains unverified.
                end_aligned=datetime.fromtimestamp(int(end.timestamp())//seconds*seconds,timezone.utc)
                start_aligned=datetime.fromtimestamp(int(start.timestamp())//seconds*seconds,timezone.utc)
                result=store.ingest_mt5(mt5,symbol,timeframe,start_aligned,end_aligned,spec.point,price_basis=basis,
                    timestamp_metadata=timestamp_metadata,request_axis_offset_seconds=request_axis_offset_seconds)
                report["datasets"].append({"symbol":symbol,"timeframe":timeframe,"version":result.version,
                                            "rows":result.rows,"sha256":result.file_sha256,"quality":result.quality})
            except Exception as exc:
                report["errors"].append({"symbol":symbol,"timeframe":timeframe,"error":str(exc)})
        if include_ticks:
            try: report["ticks"].append(store.ingest_ticks(mt5,symbol,start,end,
                timestamp_metadata=timestamp_metadata,request_axis_offset_seconds=request_axis_offset_seconds))
            except Exception as exc: report["errors"].append({"symbol":symbol,"kind":"ticks","error":str(exc)})
    directory=Path(root)/"sync_reports"; directory.mkdir(parents=True,exist_ok=True)
    from uuid import uuid4
    destination=directory/f"sync-{uuid4().hex}.json"
    with destination.open("x",encoding="utf-8") as handle: json.dump(report,handle,indent=2,allow_nan=False)
    report["report_path"]=str(destination.resolve())
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",default="var/history")
    parser.add_argument("--symbols",nargs="+",required=True)
    parser.add_argument("--timeframes",nargs="+",choices=list(TIMEFRAMES),default=list(TIMEFRAMES))
    parser.add_argument("--lookback-days",type=float,default=7)
    parser.add_argument("--terminal")
    parser.add_argument("--ticks",action="store_true")
    parser.add_argument("--interval-seconds",type=int,default=0)
    parser.add_argument("--request-offset-seconds",type=int,default=0)
    args=parser.parse_args()
    if args.lookback_days<=0 or args.interval_seconds<0: parser.error("Positive lookback and nonnegative interval required")
    import MetaTrader5 as mt5
    if not (mt5.initialize(args.terminal) if args.terminal else mt5.initialize()):
        raise SystemExit(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        while True:
            end=datetime.now(timezone.utc)
            report=sync_history(mt5,args.root,args.symbols,end-timedelta(days=args.lookback_days),end,args.timeframes,
                include_ticks=args.ticks,request_axis_offset_seconds=args.request_offset_seconds)
            print(json.dumps({"report_path":report["report_path"],"datasets":len(report["datasets"]),"errors":len(report["errors"])}),flush=True)
            if not args.interval_seconds: return 1 if report["errors"] else 0
            time.sleep(args.interval_seconds)
    finally: mt5.shutdown()


if __name__=="__main__": raise SystemExit(main())
