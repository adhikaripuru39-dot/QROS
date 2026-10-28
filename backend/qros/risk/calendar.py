"""Trading-day calendar: firm-timezone daily resets, session windows."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from qros.config.schemas import DailyReset, TradingHours


def _aware(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return now


def trading_day(now: datetime, reset: DailyReset) -> date:
    """The firm trading date that `now` belongs to.

    Convention: a trading day is labelled by the firm-local date on which its
    reset window *starts*. It runs from reset-time on D (local) to reset-time on
    D+1. E.g. with a 17:00 New York reset, Monday 18:00 NY belongs to day
    "Monday" and Tuesday 09:00 NY also belongs to day "Monday".
    """
    local = _aware(now).astimezone(ZoneInfo(reset.timezone))
    if local.time() >= reset.time:
        return local.date()
    return local.date() - timedelta(days=1)


def last_reset(now: datetime, reset: DailyReset) -> datetime:
    tz = ZoneInfo(reset.timezone)
    d = trading_day(now, reset)
    return datetime.combine(d, reset.time, tzinfo=tz).astimezone(timezone.utc)


def next_reset(now: datetime, reset: DailyReset) -> datetime:
    tz = ZoneInfo(reset.timezone)
    d = trading_day(now, reset) + timedelta(days=1)
    # combine with tz handles DST correctly for wall-clock reset times
    return datetime.combine(d, reset.time, tzinfo=tz).astimezone(timezone.utc)


def in_trading_hours(now: datetime, hours: TradingHours) -> bool:
    local = _aware(now).astimezone(ZoneInfo(hours.timezone))
    t, wd = local.time(), local.weekday()
    for s in hours.sessions:
        if s.start <= s.end:
            if wd in s.days and s.start <= t < s.end:
                return True
        else:  # overnight session e.g. 22:00-02:00, day refers to the start day
            if (wd in s.days and t >= s.start) or (((wd - 1) % 7) in s.days and t < s.end):
                return True
    return False


def minutes_to_weekend_close(now: datetime, tz_name: str = "America/New_York",
                             close: time = time(17, 0)) -> float:
    """Minutes until the FX weekly close (Friday 17:00 New York by default)."""
    tz = ZoneInfo(tz_name)
    local = _aware(now).astimezone(tz)
    days_ahead = (4 - local.weekday()) % 7
    fri = datetime.combine(local.date() + timedelta(days=days_ahead), close, tzinfo=tz)
    if fri <= local:
        fri += timedelta(days=7)
    return (fri - local).total_seconds() / 60.0


def is_weekend_market_closed(now: datetime) -> bool:
    """True between Friday 17:00 and Sunday 17:00 New York time."""
    local = _aware(now).astimezone(ZoneInfo("America/New_York"))
    wd, t = local.weekday(), local.time()
    if wd == 5:
        return True
    if wd == 4 and t >= time(17, 0):
        return True
    if wd == 6 and t < time(17, 0):
        return True
    return False
