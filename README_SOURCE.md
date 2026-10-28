# QROS-PROP

QROS connects to the installed FTMO MT5 terminal for genuine market/account
observations. The local system includes a control dashboard, independent executor,
immutable historical archives, research worker, risk engine, paper broker,
validation protocol, durable order ledger, broker-deal reconciliation, degradation
monitoring, and Windows deployment tooling.

Implementation does not establish strategy profitability or permission to trade.
Actual readiness is exposed at `/api/system/readiness` and in the dashboard.

## Current commissioning state

Local direct-MT5 demo forward testing is configured under the owner's
2026-10-24 instruction. See [demo operation and recovery](docs/DEMO_FORWARD_TEST.md).
The built-in calendar feed is attached and verified. Five unvalidated
`DEMO_TESTING` experiments have account-bound permission expiring October 31;
they do not qualify for funded/live activation. The one-time demo start is armed
and waiting for fresh broker clock and clean deal reconciliation after the
weekend. No broker fills have yet been observed. No VPS has been deployed.

- Connected account: FTMO Free Trial, USD demo. Observed initial simulated funding:
  $50,000. Current account observations come directly from MT5.
- Seven instruments captured across M1/M5/M15/H1/H4/D1: 42 versioned bar archives,
  plus seven genuine recent bid/ask tick archives.
- Last open-market broker clock offset calibrated from advancing multi-symbol
  observations: +10,800 seconds. Weekend quotes cannot establish current clock
  verification. Historical DST mappings remain explicitly unverified.
- Seven initial research jobs evaluate six price-based candidates per instrument.
  Results are recorded as research, not promoted strategies; OOS remains sealed.
- Trading mode DEMO, five selected demo experiments, host order permission true,
  live flag false. Entries are paused with an explicit pending demo arm; all
  readiness checks must pass before it starts. Telegram remains deferred.

The owner confirmed **2-Step Free Trial**. The active $50,000 profile uses
5% daily loss with a Prague-midnight balance anchor, 10% static maximum loss,
5% target, two minimum trading days and no consistency rule. See
[account sources and remaining assumptions](docs/FTMO_ACCOUNT_RULES.md).

## Start locally

Use Python 3.11+ and Node 20.19+. The existing virtual environment and frontend
installation can be reused. For a fresh installation:

```powershell
python -m venv backend/.venv
./backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
cd frontend
npm ci
npm run build
cd ..
```

Supply a private `.env` based on `.env.example`. Production requires a secret
API token of at least 32 characters. Commissioning created a local private token;
it is not printed, committed, or embedded in the frontend. Enter it from `.env`
when signing into the dashboard.

Run these as separate processes from the project directory:

```powershell
./backend/.venv/Scripts/python.exe -B run_api.py
./backend/.venv/Scripts/python.exe -B run_executor.py
./backend/.venv/Scripts/python.exe -B run_research.py
./backend/.venv/Scripts/python.exe -B run_data.py
```

The API serves the built dashboard at **http://127.0.0.1:8000/**. It never opens
MT5 or executes research. The executor owns MT5 monitoring, command processing,
protective management, reconciliation and gated signal execution. The research
worker consumes queued jobs independently. `--once` is available for the research and data workers. The data worker refreshes
read-only archives hourly and calibrates the current broker clock each cycle.

For frontend development, `cd frontend; npm run dev` serves port 5173 with an API
proxy to port 8000. For production local use, the built dashboard on port 8000
requires no Vite process. Remote/VPS access still needs the operator's TLS and
network configuration; no remote host has been deployed by this task.

## Data and research

```powershell
./backend/.venv/Scripts/python.exe -B scripts/sync_ftmo_history.py
```

The commissioning capture script preserves broker-native timestamps and records
current clock evidence; its request-axis offset is explicit. Recheck current
broker offset before future captures, especially around DST changes. Generic
periodic sync is available through `python -m qros.data.sync --help` from backend.

Queue research from Strategy Lab. Jobs bind dataset bytes, source code, costs,
protocol and runtime assumptions to reports. The worker performs a bounded 2,000-bar
pilot by default, records the selected source subrange, and preserves the final
OOS partition. Missing coverage, historical timestamp verification, historical
cost schedules, runtime equivalence, or adequate samples prevents eligibility.
Pilot P&L is explicitly a modeled research result, never observed account profit.

See `docs/RESEARCH_PROTOCOL.md`, `backend/qros/data/README.md`, and
`backend/qros/backtest/README.md` for algorithms, assumptions and limitations.

## Order and recovery controls

All strategy entries must pass evidence verification and the independent risk
gate. The durable intent is committed before submission. Unknown outcomes are
not blindly retried. Actual filled volume and broker stops are checked; partial
fills pause entries. Broker deals reconcile journals by account/mode-scoped ticket
bindings, including financing and commissions. Unmanaged positions are reported
and block clean reconciliation.

A risk halt blocks entries. The default `flatten_managed` policy attempts closure
of QROS-managed positions when host execution is enabled; it does not silently
close unrelated manual positions. The owner-triggered KILL command has separate
account-wide cancellation/closure semantics and a durable kill flag before calls.
Restart always pauses a previously running session. An OS-owned executor lock
prevents multiple writers for the configured terminal.

Paper balances, costs and fills are explicit simulations using genuine quotes.
Paper startup requires explicit capital/cost assumptions; it never forwards an
order to MT5. All paper/deployment/strategy owner gates remain active.

## Verification and deployment

```powershell
./backend/.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider
cd frontend
npm run build
```

See `docs/OPERATIONS.md` for supervisors, same-session opt-in Scheduled Tasks,
log rotation, online SQLite backups, and restore procedures. Scheduled Tasks have
not been installed automatically. `deployment/backup_sqlite.py` preserves SQLite
WAL contents through the backup API and checks restored database integrity.

Outstanding commissioning gates include verified firm-reset anchors, trial expiry, complete historical session/time/cost evidence,
validated runtime-equivalent strategies, owner approvals, and measured forward
paper/demo execution. Passing unit tests cannot substitute for those observations.


## Five-strategy library and weekly review

Open Strategy Lab for five sourced research templates, configurable ATR exits,
versioned research jobs and immutable weekly review snapshots. Proposed changes
fork a new IDEA version without inheriting approvals. Paper/demo/live logs remain
separate; no forward trades means no forward evidence. See
[the workflow](docs/STRATEGY_LIBRARY.md). No automatic optimization or activation.


## Built-in MT5 news calendar

A compiled read-only MQL5 calendar exporter feeds a fail-closed entry filter.
Risk Center shows freshness and instrument blackouts. Local attachment is still
pending after UI control was stopped; missing exports block entries. This does
not manage existing SL/TP/pending execution around funded FTMO restrictions.
See [calendar setup and funded VPS gates](docs/MT5_NEWS_AND_FUNDED_VPS.md).
