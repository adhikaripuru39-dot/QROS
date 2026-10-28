# QROS operations

The readiness page reports observed prerequisites. A passing check is not an
authorization to trade. Research candidates start inactive; changing the
dashboard mode does not bypass lifecycle, evidence, host or per-order risk gates.
Telegram is deferred until the market/execution path has been verified.

For the owner's explicitly authorized local unvalidated broker demo experiment,
see [Demo forward testing](DEMO_FORWARD_TEST.md). Its separate, expiring
`DEMO_TESTING` permission does not require pretending research validation passed
and never grants funded/live eligibility.

## Prepare the Windows host

Use Python 3.11 or later, a supported MetaTrader 5 terminal, and one Windows user
session for the terminal and QROS. Sign in to the intended broker account in the
terminal. Confirm the server, demo/real classification and account currency.
Terminal authorization failures require a valid terminal login; the dashboard
must continue to show unavailable observations until that succeeds.

Keep the repository on a local disk for deployment. Avoid sync software moving
SQLite/WAL files while services are running. Store the private root `.env`
outside source control with a random API token of at least 32 characters. Start
with `QROS_ORDER_EXECUTION_ENABLED=false`, `QROS_LIVE_TRADING_ENABLED=false`, and
`QROS_RESUME_ON_RESTART=false`. Supply broker symbol aliases, verified contract
values and the firm's actual rules. Example profiles intentionally block entry.
Define a verified news calendar if the configured policy requires one.

From the project root in PowerShell:

```powershell
./deployment/setup_vps.ps1 -InstallDependencies
./deployment/run_backend.ps1
```

Open two additional terminals for the independent processes:

```powershell
./deployment/run_executor.ps1
./deployment/run_worker.ps1
./deployment/run_data.ps1
```

The API defaults to `127.0.0.1:8000`, one worker. The dashboard development server
uses port 5173; its Vite proxy forwards `/api` locally. Build the frontend for a
production deployment, then serve the built files behind an authenticated TLS
reverse proxy with `/api` forwarded to the loopback API. Restrict access to the
owner's VPN or local host. Binding the API elsewhere requires an explicit
`-BindAddress` argument; configure the firewall and proxy before doing so.

Each script requires `.env`, validates the API token without printing it, and
forces restart recovery to pause new entries. Supervisors restart crashed
processes with exponential backoff capped at 30 seconds. Use `-NoRestart` for
single-process diagnostics. The executor's process lock prevents duplicate
executors; a second instance must not be used as a way to recover a stuck order.

## Optional login-session supervision

`deployment/install_watchdog.ps1 -Install` explicitly registers four scheduled
tasks for the current user's next login. It does not start them, elevate them,
replace existing tasks or store a Windows password. MT5 depends on the user's
logged-in interactive session, so this is not an unattended session-zero Windows
service. Review existing tasks named `QROS-backend`, `QROS-executor`, and
`QROS-worker`, and `QROS-data` before changing their definitions. The installer is optional and
is never run by setup.

## Commissioning sequence

1. Leave entry and live host locks disabled. Inspect readiness checks and the
   MT5 probe. Account, quote, position and pending-order queries must all be
   genuine and timestamped. An incomplete query means unknown, not zero.
2. Queue development/validation research for an explicit symbol and interval.
   Inspect dataset provenance, coverage, execution-cost assumptions and rejected
   candidates. The standard dashboard queue keeps final OOS sealed. A valid
   research job can still produce no eligible candidate.
3. Run paper only with explicit initial balance, commission, slippage and swap
   assumptions. Its prices are observed market quotes; its capital, orders and
   P/L are simulated. The paper ledger uses fixed account-currency tick values,
   configured margin per lot, and UTC-midnight daily swaps without a triple
   rollover calendar. It does not model market depth, queue priority or partial
   liquidity. These assumptions must appear in any paper interpretation.
4. Verify protective-stop gap fills, duplicate submission prevention, stale-feed
   rejection, disconnect/reconnect and restart recovery. Reconcile journal rows
   against the durable execution ledger and broker-observed deal history.
5. Promote a candidate through evidence gates and owner approvals only after
   it meets the acceptance policy. Commission demo execution on a verified demo
   account; capture actual rejects, fills, costs and recovery behavior. Changing
   host execution locks is a separate operator action.
6. Live activation remains owner controlled and requires the configured typed
   confirmation, verified real account, current risk state, approved evidence,
   host locks and a functioning recovery procedure. Historical or paper success
   cannot establish future profitability.

The degradation watchdog accepts independently verified, immutable benchmarks
and chronological completed net trade outcomes. It requires a minimum sample
before recommending suspension. Its Wilson win-rate comparison and net-expectancy
floor are monitoring heuristics, not lifecycle approvals. Repeated observations,
serial dependence and changing payoff sizes limit statistical interpretation.

## Failure and recovery

Read the last observed timestamp before interpreting a displayed balance or P/L.
An API connection does not imply a connected broker or an armed executor. Pause
entries for a stale/missing feed, reconciliation mismatch, uncertain order
outcome, invalid evidence or risk breach. Query order/deal history using the
durable client identity before any resubmission. Never clear the order ledger to
resolve an uncertain broker response.

After a process crash, reconnect and reconcile first. A previously running
executor recovers with entries paused. Confirm protective broker stops on each
managed position; existing broker stops continue independently of the API.
Use the command result to determine which close/cancel requests were confirmed.
If the broker cannot be queried, a kill request can engage the local entry block
without proving that broker positions were closed. Verify directly in MT5 and
resolve every per-ticket failure before an owner resume.

The configured halt policy distinguishes blocking new entries and attempting to
flatten managed exposure. Inspect the audited command and policy; do not assume
that an entry halt itself closes a position or that unrelated manual trades are
managed by QROS.

## Logs and backups

Supervisors write timestamped logs under `var/logs`. Each service retains its
30 most recent log files and rotates around 15 MiB (checked every 100 lines).
Retention only removes matching files inside that directory and refuses linked
files. Review logs for accidental third-party secret output before sharing.

Run `./deployment/backup.ps1` to use SQLite's online backup API for the main
database and auxiliary SQLite accounts. Config files are copied; `.env` is
excluded. Fourteen timestamped backup directories are retained by default.
This is a local recovery copy, so also maintain encrypted off-host backups of
the generated backup, source/config versions and immutable dataset/research
artifacts. Non-SQLite deployments require their database's native backup tools.

For recovery, stop all QROS processes, retain the current database separately,
restore the database/config backup into an isolated test deployment, and perform
integrity checks and broker reconciliation. Restore the private environment
from an encrypted secret store. Confirm entry/live locks are disabled and
verify timestamps, evidence hashes and journal/ledger consistency before using
the restored account. Never restore a historical database while a live executor
is connected and capable of submitting orders.


## MT5 built-in calendar and funded Standard staging

See [MT5 news and funded VPS commissioning](MT5_NEWS_AND_FUNDED_VPS.md).
The optional login-task installer now includes the hourly data worker. The
read-only calendar EA must remain attached in the terminal; Scheduled Tasks do
not themselves attach it. The built production dashboard is served by the API
on loopback port 8000. No funded approval or remote deployment is implied.
