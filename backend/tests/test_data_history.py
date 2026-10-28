from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pandas as pd
import pytest
from qros.data import HistoryStore, validate_bars

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def rows(times=(0, 60, 120)):
    return pd.DataFrame([dict(time=int(START.timestamp())+t, open=1.,high=1.1,low=.9,close=1.,
                             tick_volume=2, spread=10,real_volume=0) for t in times])


def test_gaps_and_duplicates_are_not_silently_repaired():
    quality = validate_bars(rows((0,0,120)), "M1", START, START+timedelta(minutes=3))
    assert quality["duplicate_times"] == 1
    assert quality["missing_expected_bars"] == 1
    assert not quality["usable"]
    assert not quality["coverage_proven"]


def test_empty_history_is_reported_unusable():
    from qros.data.history import REQUIRED
    quality = validate_bars(pd.DataFrame(columns=REQUIRED), "M1", START, START+timedelta(minutes=3))
    assert not quality["usable"]
    assert quality["missing_expected_bars"]==3


def test_explicit_session_calendar_and_ohlc_validation():
    frame = rows((0,120))
    args = ("M1",START,START+timedelta(minutes=3))
    quality = validate_bars(frame,*args,expected_times=[START,START+timedelta(minutes=2)])
    assert quality["usable"] and quality["coverage_proven"]
    frame.loc[0,"high"] = .5
    assert validate_bars(frame,*args)["invalid_rows"] == 1


class MT5:
    TIMEFRAME_M1 = 1
    def copy_rates_range(self,*_): return rows().to_records(index=False)
    def terminal_info(self): return SimpleNamespace(build=1,maxbars=1000)
    def account_info(self): return SimpleNamespace(server="Demo")


def test_ingestion_immutable_versions_and_tamper_detection(tmp_path):
    store = HistoryStore(tmp_path)
    args = (MT5(),"EURUSD","M1",START,START+timedelta(minutes=3),.00001)
    a = store.ingest_mt5(*args,price_basis="bid",now=START+timedelta(minutes=4))
    b = store.ingest_mt5(*args,price_basis="bid",now=START+timedelta(minutes=4))
    assert a.version != b.version
    frame, manifest = store.load(a.version)
    assert len(frame) == 3 and manifest.file_sha256 == a.file_sha256
    assert manifest.source["server"] == "Demo"
    with (tmp_path/a.version/"bars.parquet").open("ab") as handle: handle.write(b"tampered")
    with pytest.raises(ValueError,match="hash"): store.load(a.version)
    with pytest.raises(ValueError): store.load("../escape")


def test_incomplete_current_bar_and_naive_dates_rejected(tmp_path):
    store = HistoryStore(tmp_path)
    with pytest.raises(ValueError):
        store.ingest_mt5(MT5(),"EURUSD","M1",START.replace(tzinfo=None),START,.00001,price_basis="bid")
    manifest = store.ingest_mt5(MT5(),"EURUSD","M1",START,START+timedelta(seconds=150),.00001,
                               price_basis="bid",now=START+timedelta(seconds=150))
    assert manifest.rows == 2
    assert manifest.quality["missing_expected_bars"] == 1


def test_tick_archive_preserves_real_quotes_and_does_not_claim_complete(tmp_path):
    class TickMT5(MT5):
        COPY_TICKS_ALL = 0
        def copy_ticks_range(self, *_):
            return pd.DataFrame([dict(time=int(START.timestamp()),time_msc=int(START.timestamp()*1000),
                                      bid=1.1,ask=1.1001,last=0.,volume=0,flags=6,volume_real=0.)]).to_records(index=False)
    store = HistoryStore(tmp_path)
    manifest = store.ingest_ticks(TickMT5(),"EURUSD",START,START+timedelta(seconds=1))
    frame, verified = store.load_ticks(manifest["version"])
    assert frame.iloc[0].ask == 1.1001
    assert verified["quality"]["invalid_quote_rows"] == 0
    assert not verified["quality"]["coverage_proven"]


def test_automated_sync_reports_errors_and_never_approves_coverage(tmp_path):
    from qros.data.sync import sync_history
    class SyncMT5(MT5):
        def symbol_info(self,symbol):
            return SimpleNamespace(point=.00001,chart_mode=0) if symbol=="EURUSD" else None
    report=sync_history(SyncMT5(),tmp_path,["EURUSD","UNKNOWN"],START,START+timedelta(minutes=3),["M1"])
    assert len(report["datasets"])==1
    assert len(report["errors"])==1
    assert not report["datasets"][0]["quality"]["coverage_proven"]
    assert __import__("pathlib").Path(report["report_path"]).is_file()


def test_current_broker_skew_does_not_normalize_historical_dst(tmp_path):
    offset=10800
    class ShiftedMT5(MT5):
        def copy_rates_range(self,*_):
            frame=rows();frame["time"]+=offset;return frame.to_records(index=False)
    store=HistoryStore(tmp_path)
    reported_start=START+timedelta(seconds=offset)
    manifest=store.ingest_mt5(ShiftedMT5(),"EURUSD","M1",reported_start,reported_start+timedelta(minutes=3),.00001,
        price_basis="bid",now=START+timedelta(minutes=4),request_axis_offset_seconds=offset,
        timestamp_metadata={"observed_current_offset_seconds":offset})
    frame,_=store.load(manifest.version)
    assert frame.iloc[0].time==int(START.timestamp())+offset
    assert "time_utc" not in frame
    assert manifest.first_bar_utc is None
    assert manifest.first_bar_reported_epoch==int(START.timestamp())+offset
    assert not manifest.quality["timestamp_verified"]
    assert not manifest.quality["coverage_proven"]


def test_only_verified_historical_schedule_adds_separate_utc_column(tmp_path):
    epoch=int(START.timestamp())
    schedule=[{"reported_start":epoch,"reported_end":epoch+120,"utc_offset_seconds":10800,"verified":True,"source":"broker-offset-log-a"},
              {"reported_start":epoch+120,"reported_end":epoch+180,"utc_offset_seconds":7200,"verified":True,"source":"broker-offset-log-b"}]
    store=HistoryStore(tmp_path)
    manifest=store.ingest_mt5(MT5(),"EURUSD","M1",START,START+timedelta(minutes=3),.00001,
        price_basis="bid",now=START+timedelta(minutes=4),timestamp_metadata={"historical_offset_schedule":schedule})
    frame,_=store.load(manifest.version)
    assert list(frame.time)==[epoch,epoch+60,epoch+120]
    assert list(frame.time_utc)==[epoch-10800,epoch+60-10800,epoch+120-7200]
    assert manifest.quality["timestamp_verified"]
    assert manifest.first_bar_utc is not None
    schedule[1]["verified"]=False
    invalid=store.ingest_mt5(MT5(),"EURUSD","M1",START,START+timedelta(minutes=3),.00001,
        price_basis="bid",now=START+timedelta(minutes=4),timestamp_metadata={"historical_offset_schedule":schedule})
    assert not invalid.quality["timestamp_verified"]
