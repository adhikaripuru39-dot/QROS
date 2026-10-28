"""Finalize the owner's archival copy after Robocopy completes. No broker calls."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib,json,os,shutil,sqlite3,sys
from contextlib import closing

SOURCE=Path(r'C:\Users\adhik\.gemini\antigravity-ide\scratch\qros-prop')
DEST=Path(__file__).resolve().parent
assert DEST.name=='QROS-PROP-Complete-2026-10-24' and DEST.parent.name=='Desktop'
if (DEST/'COPY_MANIFEST.json').exists():raise RuntimeError('Copy already prepared; refusing to overwrite its staging record')
sys.path.insert(0,str(SOURCE/'backend'))
from qros.config.settings import Settings
from qros.db.session import session_factory,session_scope
from qros.db.models import ControlState,SystemState,ControlCommand
from qros.audit.log import record,verify_chain
from sqlalchemy import select
from sqlalchemy.engine import make_url

settings=Settings(_env_file=SOURCE/'.env')
source_db=Path(make_url(settings.database_url).database)
target_db=DEST/'var/qros.db'
temporary=target_db.with_name('qros-copy-snapshot.tmp')
with closing(sqlite3.connect(source_db.resolve().as_uri()+'?mode=ro',uri=True)) as original:
    with closing(sqlite3.connect(temporary)) as snapshot:
        original.backup(snapshot)
        assert snapshot.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
os.replace(temporary,target_db)

# Preserve the source README and environment exactly before staging the copy.
shutil.copy2(DEST/'README.md',DEST/'README_SOURCE.md')
private=DEST/'.env'
raw=private.read_text(encoding='utf-8-sig');lines=raw.splitlines()
updates={'QROS_DATABASE_URL':'sqlite:///'+target_db.as_posix(),
    'QROS_CONFIG_DIR':(DEST/'config').as_posix(),'QROS_DATA_DIR':(DEST/'var/data').as_posix(),
    'QROS_LOG_DIR':(DEST/'var/logs').as_posix(),'QROS_ORDER_EXECUTION_ENABLED':'false',
    'QROS_LIVE_TRADING_ENABLED':'false','QROS_RESUME_ON_RESTART':'false','QROS_BROKER_ADAPTER':'none'}
for key,value in updates.items():
    indices=[i for i,line in enumerate(lines) if line.startswith(key+'=')]
    if indices:lines[indices[0]]=key+'='+value
    else:lines.append(key+'='+value)
private.write_text('\n'.join(lines)+'\n',encoding='utf-8')
now=datetime.now(timezone.utc)
with session_scope(session_factory('sqlite:///'+target_db.as_posix())) as db:
    ctrl=db.get(ControlState,1)
    ctrl.trading_mode='off';ctrl.run_state='stopped';ctrl.active_strategy_ids=[];ctrl.updated_at=now
    arm=db.get(SystemState,'demo_forward_arm')
    if arm:
        arm.data={**arm.data,'pending':False,'cancelled':'desktop_archive_copy'};arm.updated_at=now
    for command in db.execute(select(ControlCommand).where(ControlCommand.status=='pending')).scalars():
        command.status='rejected';command.result={'reasons':['DESKTOP_ARCHIVE_COPY_NOT_RUNNING']};command.processed_at=now
    record(db,'owner-copy-preparation','desktop.copy.staged',{
        'source':str(SOURCE),'destination':str(DEST),'orders_enabled':False,'adapter':'none',
        'database_snapshot':'sqlite_online_backup','source_runtime_unchanged':True})
with session_scope(session_factory('sqlite:///'+target_db.as_posix())) as db:
    audit=verify_chain(db);assert audit['ok']

token=settings.api_token.get_secret_value()
(DEST/'DASHBOARD_LOGIN_PRIVATE.txt').write_text(
    'QROS PRIVATE OWNER LOGIN\n\n'
    'Current running dashboard: http://127.0.0.1:8000/\n'
    'Optional archive dashboard, only after starting it on port 8001: http://127.0.0.1:8001/\n'
    'Username: none\nField: API bearer token\nToken: '+token+'\n\n'
    'Paste only the token into the password field; do not add the word Bearer.\n'
    'Click Connect to desk. Refreshing the page requires signing in again.\n'
    'This is the dashboard credential, not the MT5 password.\n'
    'Keep this file and .env private. This Desktop is inside OneDrive.\n',encoding='utf-8')

readme=r'''# QROS-PROP - complete Desktop copy

Prepared: __DATE__ (Asia/Katmandu).

This is the complete local project copy, including hidden configuration,
backend virtual environment, frontend dependencies/build, research code,
immutable datasets, SQLite data, logs, tests, MQL5 source and backups.
The original README is preserved as [README_SOURCE.md](README_SOURCE.md).

## Dashboard login

- Current running dashboard: http://127.0.0.1:8000/
- There is no username. The login field is **API bearer token**.
- Open [DASHBOARD_LOGIN_PRIVATE.txt](DASHBOARD_LOGIN_PRIVATE.txt) for the actual token.
- Paste the token alone into the password field and click **Connect to desk**.
- The same credential is `QROS_API_TOKEN` in the private root `.env`.
- Credentials stay in browser memory; refreshing the page requires login again.
- Dashboard authentication does not log in to MT5. The terminal uses its existing
  broker session. No MT5 password is supplied in this README.
- Port 8000 currently belongs to the original running installation. It will not
  work if that API is stopped. This copied folder has not been started.

This Desktop is inside OneDrive. The private login file, `.env`, account data and
private files inside the full backup are sensitive; keep this folder private.

## Original installation versus this copy

Original, currently commissioned installation:

`C:\Users\adhik\.gemini\antigravity-ide\scratch\qros-prop`

This copy:

`C:\Users\adhik\OneDrive\Desktop\QROS-PROP-Complete-2026-10-24`

The original is configured for the reviewed $50,000 FTMO 2-Step Free Trial demo.
At the last commissioning check, it was paused with a one-time demo start armed,
waiting for fresh broker-clock observations and clean deal reconciliation during
the closed weekend market. Its calendar feed was genuine, fresh and complete.
That is a dated observation, not a guarantee of the current running state; inspect
Trading Control and Market Readiness on the dashboard.

This copy deliberately starts **OFF / STOPPED**, with no active strategies,
no pending arm, broker adapter `none`, and order/live/restart-resume flags false.
Its `.env` points to its own copied database, config, logs and data directories.
The dashboard token is retained for the owner. The original services, login tasks,
configuration and trading state were not changed by making this copy.

The copied database was replaced with a consistent SQLite online-backup snapshot,
integrity-checked, and then given an audited archive-staging entry. Transient WAL
and shared-memory sidecars and the two active worker process locks were omitted
from the file copy. Junctions were not
followed. Other files are a file-by-file copy, not an atomic whole-disk snapshot;
active source log files may have advanced during copying.

Do not start a second trading executor for this account. Existing QROS login tasks
still point to the original folder. Do not reinstall them from this archive while
the original installation owns those tasks. For active deployment, use a normal
local disk outside OneDrive rather than a synced SQLite runtime directory.

## What is implemented

| Area | Implementation |
| --- | --- |
| Dashboard/API | React/TypeScript production dashboard, FastAPI owner-token authentication, loopback API, command results and readiness observations |
| Market data | Read-only MT5 observations; versioned Parquet bar/tick archives and source/quality metadata |
| Signals | Completed bars, explicit ATR stops/targets, stale/gap rejection, durable signal logs and stable order identities |
| Execution | Actual MT5 market-order adapter, preflight checks, durable intent before send, duplicate prevention, fill/stop verification and uncertain-outcome pause |
| Risk | Firm/account binding, daily reset anchors, loss limits, spread, session, exposure, position count, sizing and margin gates |
| Calendar | Read-only MT5 calendar exporter and fresh-snapshot entry filter |
| Research | Queued backtests, development/validation splits, evidence binding, sealed final OOS and lifecycle governance |
| Reviews | Per-strategy Monday-based Asia/Katmandu weekly reports, immutable notes, broker journal and separate paper/demo/live results |
| Recovery | Independent supervisors, process locks, pause on restart, broker reconciliation, online SQLite backups and tested isolated restore |
| Deployment | Windows setup/start scripts and opt-in interactive-user login tasks |

Telegram is deferred. No VPS has been deployed by this copy operation.

## Five strategy experiments

| Family | Initial instrument | Timeframe |
| --- | --- | --- |
| Channel trend following | EURUSD | H1 |
| Trend pullback continuation | EURUSD | H1 |
| Range mean reversion | EURUSD | M15 |
| Volatility squeeze breakout | XAUUSD | H1 |
| Failed breakout reversal | XAUUSD | M15 |

These exact variants are unvalidated research experiments. They are not a ranking
of the most profitable strategies. Earlier ineligible research remains recorded;
no failed evidence was changed to pass. Source links, entry rules and limitations
are available in Strategy Lab and `docs/STRATEGY_LIBRARY.md`.

The original installation has a separate `DEMO_TESTING` permission for these five
versions, bound to the exact demo account, runtime, implementation and firm.
It expires October 31, 2026 at approximately 09:34 Asia/Katmandu. It never grants
funded/live permission, and parameter/code/account changes require review.
The copy retains those historical records but cannot execute with its disabled
host configuration and OFF state.

Commissioned original demo limits:

- 0.05% of the smaller balance/equity per trade, approximately $25 at $50,000.
- One open position; at most six entries per day.
- 0.1% aggregate open stop risk.
- 0.5% internal daily/session loss stop; 2% internal total stop.
- Protective broker stops, genuine quotes, news freshness and reconciliation
  are mandatory. Gap losses can exceed modeled stop risk.

The active profile is a $50,000 **2-Step Free Trial**: modeled 5% daily and 10%
static total firm loss limits, Prague daily reset, 5% trial target and two minimum
trading days. This is not a funded Standard profile. The configured $7 per lot
round-turn commission is a conservative unverified model assumption, not a proven
broker fee. Funded Standard rules and account programme must be reviewed separately.

## Built-in MT5 calendar

Correct local terminal:

`C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe`

Do not confuse it with the separate generic MetaTrader 5 / MetaQuotes demo terminal.

Exporter source: `mt5/QROSCalendarExport.mq5`. It contains no order functions,
DLL imports or WebRequest calls. It exports every 30 seconds to the actual
terminal data directory:

`C:\Users\adhik\AppData\Roaming\MetaQuotes\Terminal\81A933A9AFC5DE3C23B15CAB19C63850\MQL5\Files\QROS\calendar.json`

The owner attached the exporter to a spare chart. Verified snapshots had schema 2,
257 calendar values, complete coverage, zero query errors and seven currencies.
QROS blocks new entries for moderate/high-impact events within five minutes before
and after, and for missing/stale/invalid coverage (maximum age 120 seconds).

Keep MT5 and that chart/exporter running. The Risk Center displays actual feed
status. This filter blocks new entries only: it does not flatten holdings or
prevent SL/TP/pending fills around news. Funded Standard compliance is unverified.
On another PC/VPS, terminal and calendar paths must be discovered and configured
again; the local user's paths will not transfer automatically.

## Dashboard sections and routine use

1. **Overview:** genuine balance/equity, timestamps, readiness, connection and risk.
2. **Strategy Lab:** hypotheses, research jobs, exact versions and weekly reviews.
3. **Trading Control:** mode, active strategy commands, start/pause/stop, demo arm
   and emergency controls. Only processed executor results confirm an action.
4. **Risk Center:** limits, reset information and native calendar status.
5. **Performance & Journal:** actual recorded trades, costs, outcomes and exports.

In the original demo installation, **Arm demo when ready** queues a one-time start
after all demo readiness checks pass. A manual control command, account/selection
change, expiry, halt or executor restart cancels that pending arm. Once consumed,
it does not repeatedly resume after failures. Start does not force a trade:
completed-bar signals and every per-order gate must still pass.

Pause/Stop preserve open positions and broker stops. The emergency kill command
can cancel pending orders and close positions across the account; inspect its
typed confirmation and per-ticket results carefully. A local halt does not prove
that the broker closed a position. Never delete the order ledger to resolve an
uncertain submission, and never blindly resend it.

## Inspect this copy without starting trading

Open PowerShell in this folder. To run only the archive API/dashboard separately:

```powershell
.\deployment\run_backend.ps1 -Port 8001
```

Then visit http://127.0.0.1:8001/ and use the private login token. Do not start the
archive executor while the original executor is running. Historical observations
in the copy are snapshots; they do not indicate a connected archive broker.

Copied Python virtual environments are not portable to a different machine, and
their pip launchers may retain original absolute paths. For a new Windows host,
preserve the included environment as an archive, create a fresh Python 3.11+
environment at `backend\.venv`, and install requirements with that host's Python:

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\deployment\setup_vps.ps1
```

The built frontend is already included in `frontend/dist`; Node is unnecessary
to serve it. To rebuild on a development host, install Node and run:

```powershell
cd frontend
npm ci
npm run build
```

After a deliberate future migration, four separate runtime scripts are available:

```powershell
.\deployment\run_backend.ps1
.\deployment\run_executor.ps1
.\deployment\run_worker.ps1
.\deployment\run_data.ps1
```

Do not run these from this archive to duplicate the original account runtime.
Migration must first stop the old owner, verify the intended MT5 account/rules,
configure new paths, review grants/limits and re-commission market observations.
Keep the API on loopback; remote access needs an appropriately configured private
network or authenticated TLS setup. The built-in MT5 platform VPS must not be
assumed to run QROS's external Python processes.

## Recovery and backups

Original login tasks: `QROS-backend`, `QROS-executor`, `QROS-worker`, `QROS-data`.
They run under the current logged-in Windows user, without storing a password.
They do not sign into Windows/MT5. The supervisors restart failed processes;
an executor restart pauses entries and cancels a pending demo arm.

Verified locally: a real owned executor was terminated, its supervisor recovered
it with a new PID, entries stayed paused, and the pending arm was cancelled.
A real online backup was also restored to an isolated broker-free database;
integrity and audit-chain checks passed and no orders were created.
A full Windows reboot/login test has not been performed.

Backup command (run against the intended installation):

```powershell
.\deployment\backup.ps1
```

Backups are under `var/backups`; secrets are excluded by that backup script.
This entire folder copy does include private configuration and prior private
implementation backups. Preserve secrets separately in an encrypted store.

For restoration, stop the intended services first, retain the current database,
restore into an isolated test location, validate SQLite/audit integrity, and
reconcile the actual broker positions/deals before re-arming. Never replace a
production database while a capable executor is connected. Do not start two
copies to recover an uncertain order.

## Weekly review and optimization

Use Monday-start weeks in Asia/Katmandu. Select the exact version and **Demo**
mode. Review actual fills/rejects, net P&L, commissions, swap, slippage,
drawdown, R-multiples, signal reasons and recovery behavior. Paper/demo/live and
modeled research remain separate. No fills means no forward profit evidence.

Save review notes and the next falsifiable hypothesis. If changing parameters,
fork a new version; do not overwrite the old evidence or repeatedly tune on
the final holdout. Review decisions do not automatically promote, renew or arm
a strategy. No scheduled weekly optimization or Telegram notifications are active.

## Verification and remaining work

- Latest completed software checks: **261 backend tests passed**, two dependency/
  synthetic-data warnings; TypeScript/Vite production build passed.
- Native MQL5 exporter compiled with zero errors/warnings; genuine feed verified.
- Actual supervisor recovery, isolated restore and audit chain verified.
- At the last acceptance check there were zero broker orders and zero trades.
- First genuine MT5 fill, stop verification and completed broker-deal
  reconciliation remain open-market acceptance work before VPS migration.
- Funded deployment is not approved; live trading remains disabled.
- Browser automation did not complete final visual dashboard verification.

Reports under `var/readiness` are dated evidence snapshots, not live monitoring.
`demo_forward_acceptance.json` describes the original commissioned runtime;
`COPY_MANIFEST.json` describes this copy's OFF/stopped staging changes.

## Folder map and detailed documentation

| Path | Contents |
| --- | --- |
| `backend/qros` | API, broker adapters, execution, risk, research, validation and reporting |
| `backend/tests` | Isolated unit/integration tests; no broker orders |
| `frontend/src`, `frontend/dist` | Dashboard source and compiled bundle |
| `config` | Firm profiles, instrument contracts and initial defaults |
| `.env`, `.env.example` | Private active configuration and non-secret template |
| `mt5` | Calendar exporter MQL5 source |
| `deployment` | Setup, service supervisors, task installer and backup tools |
| `scripts` | Commissioning, probes, inspection and recovery verification |
| `var/qros.db` | Consistent copied account/research/journal database, staged OFF |
| `var/data`, `var/research` | Market/history and research artifacts where present |
| `var/logs`, `var/backups`, `var/readiness` | Logs, backups and dated acceptance evidence |
| `.implementation-backups`, `.phase1-backups` | Historical development/recovery copies |

Read: [Operations](docs/OPERATIONS.md),
[Demo forward testing](docs/DEMO_FORWARD_TEST.md),
[MT5 news and funded limitations](docs/MT5_NEWS_AND_FUNDED_VPS.md),
[FTMO account rules](docs/FTMO_ACCOUNT_RULES.md),
[Research protocol](docs/RESEARCH_PROTOCOL.md),
[Strategy library](docs/STRATEGY_LIBRARY.md),
and [earlier commissioning](docs/COMMISSIONING_2026-10-23.md).
Earlier documents record their own historical states; use the latest demo
commissioning record for the current design and the live API for current status.
'''
(DEST/'README.md').write_text(readme.replace('__DATE__',now.astimezone(ZoneInfo('Asia/Katmandu')).strftime('%Y-%m-%d %H:%M %Z')),encoding='utf-8')

core=[]
for folder in ('backend/qros','backend/tests','frontend/src','config','deployment','mt5','scripts','docs'):
    for path in (SOURCE/folder).rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts:continue
        relative=path.relative_to(SOURCE);copied=DEST/relative
        assert copied.is_file(),f'Missing copied file: {relative}'
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert hashlib.sha256(copied.read_bytes()).hexdigest()==digest,f'Copy mismatch: {relative}'
        core.append({'path':relative.as_posix(),'sha256':digest})
manifest={'prepared_at':now.isoformat(),'source':str(SOURCE),'destination':str(DEST),
    'source_runtime_unchanged':True,'database_snapshot':'sqlite_online_backup',
    'database_integrity':'ok','audit_chain':audit,'copied_runtime':{'mode':'off','run_state':'stopped',
    'broker_adapter':'none','order_execution_enabled':False,'live_trading_enabled':False,'pending_arm':False},
    'intentional_differences':['README.md (source preserved as README_SOURCE.md)',
    '.env (local copy paths, broker and trading disabled)','var/qros.db (consistent snapshot and audited OFF staging)',
    'runtime WAL/SHM and active data_worker.lock/research_worker.lock excluded',
    'COPY_LOG.txt, COPY_RETRY_LOG.txt, COPY_MANIFEST.json, DASHBOARD_LOGIN_PRIVATE.txt, PREPARE_COPY.py added'],
    'verified_core_files':core,'core_file_count':len(core),'secrets_printed':False}
(DEST/'COPY_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'destination':str(DEST),'core_files_verified':len(core),'database_integrity':'ok',
    'audit_ok':audit['ok'],'copy_trading_enabled':False,'readme':'README.md','login_file':'DASHBOARD_LOGIN_PRIVATE.txt'}))
