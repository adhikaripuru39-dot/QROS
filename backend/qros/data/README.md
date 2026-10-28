History API
===========

`HistoryStore(root).ingest_mt5(mt5, symbol, timeframe, start, end, point,
price_basis="bid", expected_times=None)` performs read-only calls against an
already initialized MT5 connection. M1/M5/M15/H1/H4/D1 are supported. Use aware
timezone-aware datetimes and an exclusive end. Query in 31-day partitions. A current
incomplete bar is omitted and appears as missing if the request includes it.

Returned immutable-version `DatasetManifest` records request boundaries,
actual boundaries, broker server, terminal build/history limit, source,
timestamp interpretation, quality flags and SHA-256 of the Parquet bytes.
`load(version)` verifies that hash before returning `(DataFrame, manifest)`.
Ingestion never overwrites an existing version; normal filesystem permissions
still allow an owner to delete or alter files, which hash verification detects.

`price_basis` must come from verified chart/instrument semantics. Last-price
exchange bars cannot be passed to the bid-bar backtester. MT5 bar spread is an
observed number of points and does not reconstruct real historical ask OHLC.
Convert spread to price with `spread * point` explicitly for modeled tests.

`validate_bars` reports invalid OHLC, nonfinite values, negative volume/spread,
duplicates, disorder, boundary violations, gaps and absolute close returns over
20% for review. No records are interpolated, reordered or silently deduplicated.
Without a supplied trading-session calendar, gaps use a continuous grid and
`coverage_proven` remains false, including around legitimate market closures.
An explicit calendar is an external assumption requiring broker verification.

Timestamp verification
----------------------

Official MT5 documentation describes UTC epochs. Actual connected FTMO terminal
observations show current reported epochs roughly 10,800 seconds ahead of the
independently observed UTC clock. Archives preserve raw `time` and `time_msc`
without assuming that the official description verifies historical timestamps.
`timestamp_metadata` records skew observations and request selection semantics.
`request_axis_offset_seconds` changes API selection/current incomplete-bar checks
only; it is never applied as a historical normalization. Collection time remains
actual UTC. Raw epoch bounds are separate manifest fields; `first_bar_utc` and
`last_bar_utc` are null without verified historical mapping.

`quality.timestamp_verified` defaults false. A `historical_offset_schedule` in
timestamp metadata must cover the entire reported request interval with sourced,
verified, continuous intervals (`reported_start`, `reported_end`,
`utc_offset_seconds`, `verified`, `source`). Only then is a separate `time_utc`
(bars) or `time_msc_utc` (ticks) added; raw fields are never overwritten. The API
validates schedule structure/coverage, not independent authenticity. Broker DST
evidence is required. A current offset cannot establish historical UTC mapping,
calendar coverage, session timing or readiness.

`ingest_ticks(mt5,symbol,start,end)` stores actual ticks in daily half-open
partitions, preserving millisecond times, bid/ask and flags without filling
missing quotes. `load_ticks(version)` checks their file hash. Irregular tick
arrival is not sufficient to prove completeness. Tick data are archived for
analysis; `BacktestEngine.run_ticks` consumes actual quotes separately from the
modeled OHLC engine.

Automated sync
--------------

`qros.data.sync.sync_history(mt5,root,symbols,start,end,timeframes,include_ticks=False)`
is callable by the service worker with an initialized connection. It detects each
instrument's actual chart mode, aligns requested bar boundaries by timeframe,
creates immutable versions and appends a unique sync report with per-symbol errors.
It never creates orders and never approves incomplete history. To initialize an
existing terminal and sync from a shell with backend on PYTHONPATH:

    python -m qros.data.sync --symbols EURUSD --lookback-days 7 --ticks

`--terminal` selects the terminal path; `--interval-seconds 300` repeats sync until
stopped. `--root` controls archive location. `--timeframes M1 H1` narrows collection.
`--request-offset-seconds` selects a raw broker request axis without certifying
historical mapping. The callable helper accepts real UTC start/end and adds the
offset solely for API selection. `scripts/sync_ftmo_history.py` captures seven
FTMO symbols and actual specifications/swaps with explicit unverified raw-time
provenance; its current request offset never certifies prior DST.
Long periodic lookbacks create repeated immutable snapshots intentionally; choose
lookback and retention storage according to observed broker availability.

Independent continuous worker
-----------------------------

`python run_data.py` from the project root, or `deployment/run_data.ps1`, starts
the independent read-only data service. `--once` runs one capture; default
`--interval-seconds 3600` waits one hour between cycles, including failures.
Defaults capture seven days for every enabled configured instrument across all
six timeframes plus fifteen minutes of genuine ticks. Original broad archives
remain intact; no data/report retention deletion occurs.

Each cycle creates a fresh `MT5Adapter(allow_orders=False)` and requires advancing
quotes with matching observed clock offset from multiple symbols. A prior cycle's
offset cannot certify a new connection or a DST change. Failure to connect,
authorize or freshly calibrate produces a truthful immutable failed report and
backs off; it never creates pretend observations or proceeds uncalibrated.
Current calibration only selects raw request windows. Historical timestamps stay
unverified unless a separate sourced historical schedule is explicitly supplied.

Archives live under `settings.data_dir/history`; immutable cycle reports under
`settings.data_dir/data_sync_reports`. `SystemState.data_sync` points to the latest
report and records its hash. `ServiceHeartbeat.data_worker` reports phase, last
status, calibrated current offset, next scheduled run and read-only operation.
The OS `data_worker.lock` prevents two workers using the same configured data
directory. Database transactions close before broker I/O, and a dedicated pulse
keeps service liveness visible during capture and waiting. Broker order methods
are never called. Use explicit broad dataset versions for repeatable research;
short rolling snapshots are fresh observations, not replacement validation data.

Official API references:
https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py
https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py
