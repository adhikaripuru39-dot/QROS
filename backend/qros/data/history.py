"""MT5 bar ingestion. API reference: https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py

No missing bars, spreads or ticks are fabricated. A bar spread is only one broker
observation, not a historical ask OHLC series. Unknown market closures stay unresolved.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import uuid

import pandas as pd

TIMEFRAMES = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600, "H4": 14400, "D1": 86400}
REQUIRED = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An explicit timezone is required")
    return value.astimezone(timezone.utc)


def validate_bars(frame: pd.DataFrame, timeframe: str, start: datetime, end: datetime,
                  expected_times=None) -> dict:
    """Validate [start,end) completed bars; optional calendar supplies expected UTC opens.

    Without a session calendar continuous-grid gaps are unresolved, including weekends;
    they must not be accepted as proved complete. Spikes are review flags, not deletions.
    """
    seconds = TIMEFRAMES[timeframe]
    start, end = _utc(start), _utc(end)
    missing_columns = sorted(set(REQUIRED) - set(frame.columns))
    if missing_columns:
        return {"usable": False, "missing_columns": missing_columns}
    finite = frame[list(REQUIRED)].apply(pd.to_numeric, errors="coerce").astype(float)
    times = pd.to_datetime(finite.time, unit="s", utc=True, errors="coerce")
    import numpy as np
    invalid = (~np.isfinite(finite)).any(axis=1)
    invalid |= times.isna()
    invalid |= (finite[["open", "high", "low", "close"]] <= 0).any(axis=1)
    invalid |= (finite.high < finite[["open", "close", "low"]].max(axis=1))
    invalid |= (finite.low > finite[["open", "close", "high"]].min(axis=1))
    invalid |= (finite[["tick_volume", "spread", "real_volume"]] < 0).any(axis=1)
    observed = set(times)
    if expected_times is None:
        expected = set(pd.date_range(start, end, freq=f"{seconds}s", inclusive="left"))
    else:
        expected = set(pd.to_datetime(list(expected_times), utc=True))
        if any(t < start or t >= end for t in expected):
            raise ValueError("Calendar observations must lie inside request")
    missing = sorted(expected - observed)
    unexpected = observed - expected
    changes = finite.close.pct_change(fill_method=None).abs()
    duplicates = int(times.duplicated().sum())
    out_of_range = int(((times < start) | (times >= end)).sum())
    monotonic = bool(times.is_monotonic_increasing)
    spikes = int((changes > .20).sum())
    return {"usable": bool(len(frame) and not invalid.any() and not duplicates and monotonic
                             and not missing and not unexpected and not out_of_range and not spikes),
            "rows": len(frame), "invalid_rows": int(invalid.sum()), "duplicate_times": duplicates,
            "monotonic": monotonic, "out_of_range": out_of_range,
            "missing_expected_bars": len(missing), "unexpected_bars": len(unexpected),
            "missing_sample_utc": [t.isoformat() for t in missing[:20]],
            "calendar": "explicit" if expected_times is not None else "continuous_grid_unverified_sessions",
            "large_return_review_flags": spikes,
            "coverage_proven": bool(expected_times is not None and not missing and not unexpected and len(frame))}


@dataclass(frozen=True)
class DatasetManifest:
    version: str
    symbol: str
    timeframe: str
    requested_start: str
    requested_end: str
    collected_utc: str
    point: float
    price_basis: str
    file_sha256: str
    rows: int
    first_bar_utc: str | None
    last_bar_utc: str | None
    source: dict
    quality: dict
    spread_semantics: str = "Observed bar spread in points; not historical ask OHLC or ticks"
    first_bar_reported_epoch: int | None = None
    last_bar_reported_epoch: int | None = None
    timestamp_metadata: dict = field(default_factory=dict)


def _timestamp_evidence(metadata, start, end):
    """Only an explicitly sourced historical schedule can establish timestamp mapping.

    Contemporary clock skew is evidence about current observations, not earlier DST.
    This validates evidence shape/coverage, not independent truth of broker records.
    """
    meta=dict(metadata or {})
    meta.setdefault("raw_timestamps_preserved",True)
    meta.setdefault("raw_timestamp_semantics","broker reported epoch; UTC interpretation unverified")
    schedule=meta.get("historical_offset_schedule",[])
    cursor=start.timestamp()
    verified=bool(schedule)
    previous_end=None
    for item in sorted(schedule,key=lambda x:x.get("reported_start",0)):
        if (item.get("verified") is not True or not item.get("source") or
            not isinstance(item.get("utc_offset_seconds"),(int,float)) or
            not math.isfinite(item["utc_offset_seconds"])):
            verified=False; break
        lo,hi=item.get("reported_start",math.inf),item.get("reported_end",-math.inf)
        if lo>cursor or hi<=lo or (previous_end is not None and lo!=previous_end):
            verified=False; break
        cursor=max(cursor,hi)
        previous_end=hi
    verified=verified and cursor>=end.timestamp()
    meta["historical_timestamp_verified"]=verified
    return meta,verified


def _utc_epoch(reported, metadata):
    for item in metadata["historical_offset_schedule"]:
        if item["reported_start"]<=reported<item["reported_end"]:
            return reported-item["utc_offset_seconds"]
    raise ValueError("Verified timestamp schedule does not cover observed row")


class HistoryStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def ingest_ticks(self, mt5, symbol: str, start: datetime, end: datetime, *,
                     timestamp_metadata=None, request_axis_offset_seconds=0) -> dict:
        """Archive genuine bid/ask observations, including flags, without quote filling.

        See https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py .
        Tick completeness cannot be inferred from irregular arrival times alone.
        """
        start, end = _utc(start), _utc(end)
        if not math.isfinite(request_axis_offset_seconds): raise ValueError("Invalid request-axis offset")
        if end <= start or end > datetime.now(timezone.utc)+timedelta(seconds=request_axis_offset_seconds):
            raise ValueError("Invalid tick interval")
        timestamp_meta,timestamp_verified=_timestamp_evidence(timestamp_metadata,start,end)
        timestamp_meta["request_axis_offset_seconds"]=request_axis_offset_seconds
        chunks, cursor = [], start
        while cursor < end:
            stop = min(cursor + timedelta(days=1), end)
            raw = mt5.copy_ticks_range(symbol, cursor, stop, mt5.COPY_TICKS_ALL)
            if raw is None:
                raise RuntimeError(f"MT5 tick history unavailable: {mt5.last_error()}")
            frame = pd.DataFrame(raw)
            if len(frame):
                required = {"time", "time_msc", "bid", "ask", "flags"}
                if required - set(frame.columns):
                    raise ValueError("Missing broker tick columns")
                frame = frame[(frame.time_msc >= cursor.timestamp()*1000) &
                              (frame.time_msc < stop.timestamp()*1000)]
                chunks.append(frame)
            cursor = stop
        frame = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(
            columns=["time", "time_msc", "bid", "ask", "flags"])
        if timestamp_verified:
            frame["time_msc_utc"]=[_utc_epoch(t/1000,timestamp_meta)*1000 for t in frame.time_msc]
        version = "ticks-" + uuid.uuid4().hex
        directory = self.root / version
        directory.mkdir(parents=True, exist_ok=False)
        path = directory / "ticks.parquet"
        frame.to_parquet(path, index=False, engine="pyarrow")
        import numpy as np
        valid = (np.isfinite(frame.bid) & np.isfinite(frame.ask) &
                 (frame.bid > 0) & (frame.ask >= frame.bid)) if len(frame) else pd.Series(dtype=bool)
        manifest = {"version": version, "symbol": symbol, "kind": "observed_ticks",
                    "requested_start": start.isoformat(), "requested_end": end.isoformat(),
                    "collected_utc": datetime.now(timezone.utc).isoformat(),
                    "provider": "MetaTrader5.copy_ticks_range(COPY_TICKS_ALL)",
                    "timestamp_metadata":timestamp_meta,
                    "server": getattr(mt5.account_info(), "server", None),
                    "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "quality": {"rows": len(frame), "invalid_quote_rows": int((~valid).sum()),
                                "duplicate_full_rows": int(frame.duplicated().sum()),
                                "monotonic_milliseconds": bool(frame.time_msc.is_monotonic_increasing),
                                "coverage_proven": False,
                                "timestamp_verified":timestamp_verified,
                                "note": "Irregular arrival gaps do not establish missing ticks; no quotes filled"}}
        with (directory / "manifest.json").open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, allow_nan=False)
        return manifest

    def load_ticks(self, version: str) -> tuple[pd.DataFrame, dict]:
        if not re.fullmatch(r"ticks-[a-f0-9]{32}", version):
            raise ValueError("Invalid tick version")
        directory = self.root / version
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        path = directory / "ticks.parquet"
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["file_sha256"]:
            raise ValueError("Tick dataset hash mismatch")
        return pd.read_parquet(path), manifest

    def ingest_mt5(self, mt5, symbol: str, timeframe: str, start: datetime, end: datetime,
                   point: float, *, price_basis: str, expected_times=None,
                   now: datetime | None = None, timestamp_metadata=None,
                   request_axis_offset_seconds=0, session_policy: str | None = None) -> DatasetManifest:
        """Read-only history calls; caller initializes the terminal. End is exclusive.

        price_basis must be supplied from instrument/chart knowledge (bid or last).
        MT5 limits available history to terminal/broker availability; quality reports it.
        """
        start, end = _utc(start), _utc(end)
        now = _utc(now or datetime.now(timezone.utc))
        if not math.isfinite(request_axis_offset_seconds): raise ValueError("Invalid request-axis offset")
        request_now=now+timedelta(seconds=request_axis_offset_seconds)
        if timeframe not in TIMEFRAMES or end <= start or end > request_now:
            raise ValueError("Invalid timeframe, interval or future end")
        if not math.isfinite(point) or point <= 0 or price_basis not in {"bid", "last"}:
            raise ValueError("Positive point and explicit bid/last basis required")
        timestamp_meta,timestamp_verified=_timestamp_evidence(timestamp_metadata,start,end)
        timestamp_meta["request_axis_offset_seconds"]=request_axis_offset_seconds
        chunks = []
        cursor = start
        while cursor < end:
            stop = min(cursor + timedelta(days=31), end)
            rates = mt5.copy_rates_range(symbol, getattr(mt5, f"TIMEFRAME_{timeframe}"), cursor, stop)
            if rates is None:
                raise RuntimeError(f"MT5 history unavailable: {mt5.last_error()}")
            chunk = pd.DataFrame(rates)
            if len(chunk):
                # MT5 returns inclusive upper endpoints. Use half-open partitions.
                chunk = chunk[(chunk.time >= cursor.timestamp()) & (chunk.time < stop.timestamp())]
                chunks.append(chunk)
            cursor = stop
        frame = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=REQUIRED)
        # Only completed bars are eligible. No sorting/deduplication hides source defects.
        frame = frame[frame.time + TIMEFRAMES[timeframe] <= request_now.timestamp()].reset_index(drop=True)
        quality = validate_bars(frame, timeframe, start, end, expected_times)
        if session_policy == "ftmo" and expected_times is None and len(frame):
            # Session-aware coverage replaces the 24/7 grid, which flags every weekend.
            from .sessions import classify_gaps
            gaps = classify_gaps(frame.time.tolist(), TIMEFRAMES[timeframe],
                                 metal=symbol.upper().startswith(("XAU", "XAG")))
            core_ok = bool(not quality["invalid_rows"] and not quality["duplicate_times"] and quality["monotonic"]
                           and not quality["out_of_range"] and not quality["large_return_review_flags"])
            quality.update({"calendar": "ftmo_session_policy", "session_gaps": gaps,
                            "missing_expected_bars": gaps["unexplained_missing_bars"], "unexpected_bars": 0,
                            "usable": core_ok and gaps["within_tolerance"],
                            "coverage_proven": core_ok and gaps["within_tolerance"]})
        quality["missing_sample_reported_axis"]=quality.pop("missing_sample_utc",[])
        quality["timestamp_verified"]=timestamp_verified
        quality["calendar_coverage_on_reported_axis"]=quality.get("coverage_proven",False)
        quality["coverage_proven"]=quality.get("coverage_proven",False) and timestamp_verified
        if timestamp_verified:
            frame["time_utc"]=[_utc_epoch(t,timestamp_meta) for t in frame.time]
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        source = {"provider": "MetaTrader5.copy_rates_range", "server": getattr(account, "server", None),
                  "terminal_build": getattr(terminal, "build", None),
                  "maxbars": getattr(terminal, "maxbars", None),
                  "api_version": getattr(mt5, "__version__", None),
                  "timestamp_semantics": "Raw broker-reported bar-open epoch preserved; UTC not assumed",
                  "timestamp_verified":timestamp_verified,
                  "request_boundaries_semantics":"API selection axis, not verified UTC event boundaries"}
        version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex
        directory = self.root / version
        directory.mkdir(parents=True, exist_ok=False)
        path = directory / "bars.parquet"
        frame.to_parquet(path, index=False, engine="pyarrow")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        times = pd.to_datetime(frame.time, unit="s", utc=True)
        manifest = DatasetManifest(version, symbol, timeframe, start.isoformat(), end.isoformat(),
                                   now.isoformat(), point, price_basis, digest, len(frame),
                                   datetime.fromtimestamp(frame.time_utc.min(),timezone.utc).isoformat() if timestamp_verified and len(frame) else None,
                                   datetime.fromtimestamp(frame.time_utc.max(),timezone.utc).isoformat() if timestamp_verified and len(frame) else None, source, quality,
                                   first_bar_reported_epoch=int(frame.time.min()) if len(frame) else None,
                                   last_bar_reported_epoch=int(frame.time.max()) if len(frame) else None,
                                   timestamp_metadata=timestamp_meta)
        with (directory / "manifest.json").open("x", encoding="utf-8") as handle:
            json.dump(asdict(manifest), handle, indent=2, allow_nan=False)
        return manifest

    def load(self, version: str) -> tuple[pd.DataFrame, DatasetManifest]:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", version):
            raise ValueError("Invalid dataset version")
        directory = self.root / version
        manifest = DatasetManifest(**json.loads((directory / "manifest.json").read_text(encoding="utf-8")))
        path = directory / "bars.parquet"
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest.file_sha256:
            raise ValueError("Dataset hash mismatch")
        return pd.read_parquet(path), manifest
