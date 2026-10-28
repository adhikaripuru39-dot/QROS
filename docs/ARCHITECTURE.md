# QROS-PROP — System Architecture

## 1. Process topology

QROS-PROP runs as **independent processes** that communicate only through the
database (SQLite in development, PostgreSQL-ready via SQLAlchemy). No trading
logic lives in the browser or in the web API process.

```
                ┌────────────────────────────┐
                │  React dashboard (browser) │  read-mostly; sends *commands*
                └─────────────┬──────────────┘
                              │ HTTPS + Bearer token, SSE
                ┌─────────────▼──────────────┐
                │  Dashboard API (FastAPI)   │  qros.api   — never talks to broker
                └─────────────┬──────────────┘
                              │ SQL (settings, command queue, snapshots, audit)
┌─────────────────────────────▼─────────────────────────────────────────┐
│                          Database                                     │
└──────▲───────────────────────▲──────────────────────────▲─────────────┘
       │                       │                          │
┌──────┴───────────┐   ┌───────┴──────────────┐   ┌───────┴─────────────┐
│ Execution service│   │ Research worker      │   │ Scheduler (Phase 5) │
│ qros.services.   │   │ qros.research        │   │                     │
│   executor       │   │ (Phase 2/3)          │   │                     │
│  ├ signal engine │   └──────────────────────┘   └─────────────────────┘
│  ├ RISK ENGINE   │  ← independent module, pure functions, own tests
│  ├ broker adapter│ ── MetaTrader 5 terminal (Windows) ── Broker
│  └ reconciliation│
└──────────────────┘
```

Key properties

* **Dashboard ≠ executor.** The API only writes rows to `control_commands`; the
  executor consumes them, acts, and writes back results. If the API dies,
  trading protection (stops, risk engine) continues. If the executor dies, the
  API reports a *stale heartbeat* rather than pretending to be connected.
* **Truthful state.** Every broker-derived value carries `observed_at`. The API
  computes staleness against `QROS_STALE_AFTER_SECONDS`. Missing data is
  returned as `null` with `available: false`, never as zero.
* **Risk engine is independent.** `qros.risk` has no import of strategies,
  signals, or broker code. It receives plain dataclasses and returns a decision
  plus reasons. Strategy profiles cannot alter it; only validated firm/internal
  limit configuration can.
* **Live trading is triple-gated:** env var `QROS_LIVE_TRADING_ENABLED=true` on
  the VPS **and** an owner-authorised `set_mode=live` command with a typed
  confirmation phrase **and** at least one strategy in `LIVE_APPROVED`/`ACTIVE`.

## 2. Pipeline (target state)

Research engine → Strategy registry → Signal engine → Independent risk engine →
MT5 execution adapter → Broker reconciliation → Database → Dashboard.

## 3. Module map

| # | Concern                | Package                         | Phase |
|---|------------------------|---------------------------------|-------|
| 1 | Research               | `qros.research`                 | 2–3   |
| 2 | Historical data        | `qros.data`                     | 2     |
| 3 | Validation             | `qros.validation`               | 3     |
| 4 | Strategy registry      | `qros.governance`, DB `strategies` | 1 (lifecycle) |
| 5 | Signal generation      | `qros.signals`                  | 4     |
| 6 | Risk engine            | `qros.risk`                     | 1 (core), 4 (live wiring) |
| 7 | Execution              | `qros.broker`, `qros.services`  | 1 (interfaces + MT5 read), 4 |
| 8 | Monitoring             | `qros.services.executor` heartbeat | 1 |
| 9 | Dashboard API          | `qros.api`                      | 1     |
|10 | Audit & reporting      | `qros.audit`                    | 1 (hash-chained log) |

## 4. Repository layout

```
qros-prop/
├─ backend/
│  ├─ qros/
│  │  ├─ api/            FastAPI app + routers (dashboard API only)
│  │  ├─ audit/          append-only, SHA-256 hash-chained audit log
│  │  ├─ broker/         BrokerAdapter interface, MT5 adapter, Null adapter
│  │  ├─ config/         pydantic schemas: firm rules, internal limits, instruments
│  │  ├─ db/             SQLAlchemy models + session
│  │  ├─ governance/     strategy lifecycle state machine
│  │  ├─ risk/           drawdown rules, position sizing, pre-trade gate, exposure
│  │  ├─ services/       executor (independent process), settings store
│  │  ├─ research/ data/ validation/ signals/   (later phases)
│  ├─ tests/
│  ├─ requirements.txt   (direct deps, pinned)  requirements.lock (full freeze)
├─ config/
│  ├─ firms/*.yaml       firm rule profiles (examples — must be edited)
│  ├─ instruments.yaml   instrument defaults
├─ frontend/             React + TypeScript + Tailwind + lightweight-charts
├─ scripts/              install / run scripts (PowerShell)
├─ docs/                 ARCHITECTURE, API, STATUS, VPS_DEPLOYMENT, GOVERNANCE
```

## 5. Data model (Phase 1)

| Table | Purpose |
|-------|---------|
| `settings` / `settings_history` | Versioned JSON settings (active firm profile, internal limits, instruments, trading hours). Every write is validated + audited. |
| `control_state` | Single row: trading mode, run state (stopped/running/paused_entries/halted), kill flag, halt reason. Written **only** by the executor. |
| `control_commands` | Queue of commands from the dashboard; executor marks `done`/`rejected`/`failed` with result JSON. |
| `service_heartbeat` | Liveness + broker connection status per service. |
| `account_snapshots` | Broker-observed balance/equity/margin with `observed_at`. Source for equity curve. |
| `positions_snapshot` | Latest broker-reported open positions. |
| `risk_days` | Start-of-day anchors per firm-local trading date (for daily loss rules). |
| `risk_state` | Latest computed risk-engine evaluation (floors, usage, breaches). |
| `strategies` / `strategy_transitions` | Strategy registry + immutable lifecycle transitions. |
| `experiments` | Immutable research experiment registry (populated from Phase 2). |
| `trades` | Closed/open trades journal with `reason` explanation (populated from Phase 4). |
| `audit_log` | Hash-chained audit events. |
