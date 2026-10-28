"""Capture broker-native raw history/specifications; never submits an order.

Current broker clock offset only changes API selection boundaries. Historical
offsets, sessions and DST are not inferred. Unverified archives cannot pass UTC
coverage or live readiness gates.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys
from statistics import median
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from qros.data import HistoryStore
from qros.data.history import TIMEFRAMES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path",default=r"C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe")
    parser.add_argument("--root",default=str(ROOT/"var/data/history"))
    parser.add_argument("--days",type=int,default=180)
    parser.add_argument("--m1-days",type=int,default=30)
    parser.add_argument("--tick-minutes",type=int,default=15)
    parser.add_argument("--request-offset-seconds",type=int,default=10800)
    args=parser.parse_args()
    if min(args.days,args.m1_days,args.tick_minutes)<=0: parser.error("Lookbacks must be positive")
    import MetaTrader5 as mt5
    if not mt5.initialize(path=args.path,timeout=30000):
        raise SystemExit(f"MT5 initialization failed: {mt5.last_error()}")
    ready=ROOT/"var/readiness";ready.mkdir(parents=True,exist_ok=True)
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"orders_submitted":0,
            "historical_timestamps_verified":False,"datasets":[],"ticks":[],"errors":[]}
    try:
        account=mt5.account_info();terminal=mt5.terminal_info()
        if not account or not terminal or not terminal.connected:
            raise RuntimeError("Connected account required for observed capture")
        all_symbols=mt5.symbols_get() or ()
        wanted=["XAUUSD","EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD"]
        names=[]
        for base in wanted:
            matches=[s.name for s in all_symbols if s.name.upper().startswith(base)]
            if not matches:
                report["errors"].append({"symbol":base,"error":"broker symbol unavailable"});continue
            name=base if base in matches else matches[0]
            if not mt5.symbol_select(name,True):
                report["errors"].append({"symbol":name,"error":"Market Watch selection failed"});continue
            names.append(name)
        observations=[];last={};changed=set()
        for attempt in range(3):
            for name in names:
                stamp=time.time();tick=mt5.symbol_info_tick(name)
                if tick is None: continue
                signature=(tick.time_msc,tick.bid,tick.ask)
                if name in last and signature!=last[name]: changed.add(name)
                last[name]=signature
                observations.append({"symbol":name,"observed_utc_epoch":stamp,
                    "reported_tick_epoch":tick.time,"reported_tick_msc":tick.time_msc,
                    "bid":tick.bid,"ask":tick.ask,"reported_minus_local_seconds":tick.time_msc/1000-stamp})
            if attempt<2: time.sleep(1)
        clock={"samples":observations,"changing_symbols":sorted(changed),
               "median_observed_skew_seconds":median(x["reported_minus_local_seconds"] for x in observations) if observations else None,
               "request_axis_offset_seconds":args.request_offset_seconds,
               "request_offset_is_historical_mapping":False,
               "note":"Current clock evidence only; do not apply one offset across historical DST"}
        timestamp_meta={"raw_timestamps_preserved":True,
            "raw_timestamp_semantics":"FTMO broker reported epoch values; observed current clock offset contradicts documented UTC interpretation",
            "current_clock_observation":clock,"historical_offset_schedule":[],
            "historical_timestamp_verified":False,
            "request_offset_purpose":"Select raw broker intervals and exclude current incomplete raw bars only; no historical timestamp normalization"}
        specs={"observed_utc":datetime.now(timezone.utc).isoformat(),"server":account.server,
               "company":account.company,"currency":account.currency,"leverage":account.leverage,
               "is_demo":account.trade_mode==mt5.ACCOUNT_TRADE_MODE_DEMO,
               "terminal_build":terminal.build,"maxbars":terminal.maxbars,
               "clock":clock,"symbols":{},"historical_timestamps_verified":False,
               "swap_note":"Current observed instrument swap settings; historical rates/mode/currency conversion not inferred"}
        fields=["name","description","currency_base","currency_profit","currency_margin","digits","point",
            "chart_mode","trade_calc_mode","trade_mode","trade_contract_size","trade_tick_size",
            "trade_tick_value","trade_tick_value_profit","trade_tick_value_loss","volume_min","volume_max",
            "volume_step","volume_limit","trade_stops_level","trade_freeze_level","filling_mode",
            "order_mode","spread","spread_float","swap_mode","swap_long","swap_short",
            "swap_rollover3days","swap_sunday","swap_monday","swap_tuesday","swap_wednesday",
            "swap_thursday","swap_friday","swap_saturday","margin_initial","margin_maintenance",
            "margin_hedged","trade_exemode"]
        store=HistoryStore(args.root)
        for name in names:
            spec=mt5.symbol_info(name)
            if spec is None:
                report["errors"].append({"symbol":name,"error":"specification unavailable"});continue
            specs["symbols"][name]={f:getattr(spec,f,None) for f in fields}
        (ready/"broker_specs.json").write_text(json.dumps(specs,indent=2,allow_nan=False),encoding="utf-8")
        (ready/"broker_clock_observations.json").write_text(json.dumps(clock,indent=2,allow_nan=False),encoding="utf-8")
        for name in names:
            spec=mt5.symbol_info(name)
            if spec is None:continue
            basis="bid" if spec.chart_mode==getattr(mt5,"SYMBOL_CHART_MODE_BID",0) else "last"
            for tf,seconds in TIMEFRAMES.items():
                try:
                    current=datetime.now(timezone.utc)
                    # These datetimes label the raw broker selection axis, not historical UTC events.
                    request_now=current+timedelta(seconds=args.request_offset_seconds)
                    end=datetime.fromtimestamp(int(request_now.timestamp())//seconds*seconds,timezone.utc)
                    start=end-timedelta(days=args.m1_days if tf=="M1" else args.days)
                    manifest=store.ingest_mt5(mt5,name,tf,start,end,spec.point,price_basis=basis,
                        timestamp_metadata=timestamp_meta,request_axis_offset_seconds=args.request_offset_seconds)
                    report["datasets"].append(asdict(manifest))
                    print(json.dumps({"symbol":name,"timeframe":tf,"rows":manifest.rows,"version":manifest.version,
                                      "timestamp_verified":manifest.quality["timestamp_verified"]}),flush=True)
                except Exception as exc:
                    report["errors"].append({"symbol":name,"timeframe":tf,"error":str(exc)})
            try:
                end=datetime.now(timezone.utc)+timedelta(seconds=args.request_offset_seconds)
                manifest=store.ingest_ticks(mt5,name,end-timedelta(minutes=args.tick_minutes),end,
                    timestamp_metadata=timestamp_meta,request_axis_offset_seconds=args.request_offset_seconds)
                report["ticks"].append(manifest)
                print(json.dumps({"symbol":name,"kind":"ticks","rows":manifest["quality"]["rows"]}),flush=True)
            except Exception as exc: report["errors"].append({"symbol":name,"kind":"ticks","error":str(exc)})
    finally:
        mt5.shutdown()
        from uuid import uuid4
        path=ready/f"history_capture-{uuid4().hex}.json"
        path.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
        print(json.dumps({"report_path":str(path),"datasets":len(report["datasets"]),"ticks":len(report["ticks"]),"errors":len(report["errors"])}),flush=True)
    return 1 if report["errors"] else 0


if __name__=="__main__":raise SystemExit(main())
