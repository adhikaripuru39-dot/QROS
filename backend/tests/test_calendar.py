from datetime import datetime,time,timezone
from qros.config.schemas import DailyReset,TradingHours,Session
from qros.risk.calendar import next_reset,last_reset,in_trading_hours,is_weekend_market_closed

def test_dst_reset_window():
    reset=DailyReset(timezone='America/New_York')
    now=datetime(2026,3,8,6,tzinfo=timezone.utc)
    assert (next_reset(now,reset)-last_reset(now,reset)).total_seconds()==23*3600

def test_overnight_session():
    hours=TradingHours(timezone='UTC',sessions=[Session(start=time(22),end=time(2),days=[0])])
    assert in_trading_hours(datetime(2026,10,20,1,tzinfo=timezone.utc),hours)
    assert not in_trading_hours(datetime(2026,10,20,3,tzinfo=timezone.utc),hours)

def test_weekend_market_closed():
    assert is_weekend_market_closed(datetime(2026,10,24,12,tzinfo=timezone.utc))
