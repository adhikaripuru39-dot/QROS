"""FTMO server-time schedule and session-aware bar coverage policy.

FTMO MT5 servers publish bar times on a clock that is GMT+2 in winter and GMT+3
in summer, with daylight saving aligned to the US schedule so that the New York
17:00 close is always 00:00 server time. This module encodes that published rule
and cross-checks it against the *currently observed* broker offset; a mismatch
refuses to claim a verified historical schedule.

Limits (documented, not hidden):
* The schedule is rule-derived, not an independently obtained broker log.
* The two hours around each DST change fall on a closed-market Sunday.
* Coverage tolerance is explicit and recorded in every manifest.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SOURCE = ("FTMO server time rule: GMT+2 winter / GMT+3 summer, DST aligned to the US "
          "schedule (New York 17:00 close = 00:00 server time)")
WINTER, SUMMER = 7200, 10800
HORIZON_START, HORIZON_END = 2018, 2041

# Unexplained-gap tolerance recorded in every manifest.
TOLERANCE_FRACTION = 0.005      # of expected bars
TOLERANCE_MAX_GAP_SECONDS = 6 * 3600


def expected_broker_utc_offset(now_utc: datetime) -> int:
    """Server clock minus UTC, in seconds, per the published FTMO rule."""
    if now_utc.tzinfo is None:
        raise ValueError("aware datetime required")
    return SUMMER if now_utc.astimezone(NY).dst() else WINTER


def _transitions():
    """UTC instants where the server offset changes, with the new offset."""
    out = []
    cursor = datetime(HORIZON_START, 1, 1, tzinfo=timezone.utc)
    stop = datetime(HORIZON_END, 1, 1, tzinfo=timezone.utc)
    previous = expected_broker_utc_offset(cursor)
    while cursor < stop:
        nxt = cursor + timedelta(days=1)
        offset = expected_broker_utc_offset(nxt)
        if offset != previous:
            probe = cursor
            while probe < nxt:
                probe += timedelta(minutes=1)
                if expected_broker_utc_offset(probe) == offset:
                    break
            out.append((probe, offset))
            previous = offset
        cursor = nxt
    return out


def historical_offset_schedule():
    """Contiguous reported-axis schedule segments, each tagged verified + sourced."""
    first = datetime(HORIZON_START, 1, 1, tzinfo=timezone.utc)
    offset = expected_broker_utc_offset(first)
    start = 0
    segments = []
    for when, new_offset in _transitions():
        boundary = int(when.timestamp()) + offset      # last reported instant under old offset
        segments.append({"reported_start": start, "reported_end": boundary,
                         "utc_offset_seconds": offset, "verified": True, "source": SOURCE})
        start, offset = boundary, new_offset
    segments.append({"reported_start": start, "reported_end": int(datetime(HORIZON_END, 1, 1, tzinfo=timezone.utc).timestamp()) + offset,
                     "utc_offset_seconds": offset, "verified": True, "source": SOURCE})
    return segments


def ftmo_timestamp_metadata(observed_current_offset=None, now_utc=None):
    """Metadata for HistoryStore; verified only if the live offset matches the rule."""
    now_utc = now_utc or datetime.now(timezone.utc)
    expected = expected_broker_utc_offset(now_utc)
    meta = {"raw_timestamps_preserved": True,
            "raw_timestamp_semantics": "FTMO broker-reported epoch; UTC mapping from published server-time rule",
            "expected_current_offset_seconds": expected}
    if observed_current_offset is None or int(observed_current_offset) != expected:
        meta.update(historical_offset_schedule=[], historical_timestamp_verified=False,
                    schedule_rejected_reason="live broker offset unavailable or disagrees with published rule")
        return meta
    meta.update(historical_offset_schedule=historical_offset_schedule(),
                observed_current_offset_seconds=int(observed_current_offset),
                schedule_cross_check="live offset equals published rule at capture time")
    return meta


def classify_gaps(times, seconds, *, metal=False):
    """Classify gaps between consecutive reported bar opens.

    Explained: weekend/holiday closures (>=40h) and, for metals, the daily 00:00-01:00
    server-time break. Everything else is unexplained and counted against tolerance.
    """
    times = list(times)
    explained_weekend = explained_break = 0
    unexplained = []
    missing_unexplained = 0
    for prev, nxt in zip(times, times[1:]):
        step = nxt - prev
        if step <= seconds:
            continue
        if step >= 40 * 3600:
            explained_weekend += 1
            continue
        missing = [prev + k * seconds for k in range(1, int(step // seconds))]
        if metal and missing and all(0 <= (m % 86400) < 3600 for m in missing):
            explained_break += 1
            continue
        count = max(1, len(missing))
        missing_unexplained += count
        unexplained.append({"after_reported_epoch": int(prev), "gap_seconds": int(step), "missing_bars": count})
    expected = len(times) + missing_unexplained
    fraction = missing_unexplained / expected if expected else 0.0
    ok = (fraction <= TOLERANCE_FRACTION
          and all(g["gap_seconds"] <= TOLERANCE_MAX_GAP_SECONDS for g in unexplained))
    return {"explained_weekend_or_holiday": explained_weekend, "explained_daily_break": explained_break,
            "unexplained_gaps": len(unexplained), "unexplained_missing_bars": missing_unexplained,
            "unexplained_fraction": fraction, "within_tolerance": ok,
            "tolerance_fraction": TOLERANCE_FRACTION, "tolerance_max_gap_seconds": TOLERANCE_MAX_GAP_SECONDS,
            "unexplained_sample": unexplained[:20]}

