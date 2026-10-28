# QROS-PROP S-Tier Windows VPS Transfer & Deployment Guide

This guide details the procedure for transferring, deploying, and operating the **QROS-PROP S-Tier Institutional Trading System** on a Windows VPS.

---

## 1. System Requirements & Architecture

- **Operating System:** Windows Server 2019 / 2022 or Windows 10 / 11 Pro (64-bit).
- **Hardware Specs:** Minimum 2 vCPUs, 4 GB RAM, 20 GB free NVMe/SSD storage.
- **Software Dependencies:**
  - **Python 3.11+ (64-bit)**: Ensure *"Add Python to PATH"* is checked during installation.
  - **MetaTrader 5 (FTMO Client)**: Installed, logged into your evaluation/funded account.
- **Runtime Isolation:** All live databases and logs run on local NVMe at `C:\QROS-Runtime` to eliminate cloud storage file-locking bugs.

---

## 2. Step-by-Step VPS Setup Procedure

### Step 1: Transfer & Extract the Archive
1. Transfer `QROS-PROP-VPS-Deployment.zip` to your VPS (via Remote Desktop Clipboard, Google Drive, or SFTP).
2. Extract the archive to a permanent root directory, e.g.:
   ```text
   C:\QROS-PROP
   ```

---

### Step 2: One-Click Automated Deployment
Open PowerShell as Administrator (or simply double-click **`DEPLOY_TO_VPS.bat`**):

```powershell
cd C:\QROS-PROP
.\deployment\deploy_vps.ps1 -AccountBalance 5000
```

**What this automatically does:**
1. Validates Python 3.11+.
2. Creates an isolated local virtual environment in `backend\.venv`.
3. Installs all required institutional packages (`FastAPI`, `SQLAlchemy`, `Pandas`, `MetaTrader5`, etc.).
4. Initializes the NVMe storage directory structure (`C:\QROS-Runtime\var` and `backups`).
5. Generates a production `.env` with a unique 64-character cryptographic API Bearer Token.
6. Initializes the database and binds the active **\$5,000 FTMO 2-Step Evaluation** profile (`ftmo_5k_2step`).
7. Binds all 12 S-Tier strategy instances and verifies the internal cryptographic audit chain.

---

### Step 3: MetaTrader 5 Configuration

1. **Launch MT5 & Log In:** Open MetaTrader 5 and log into your FTMO account.
2. **Enable Algorithmic Trading:**
   - In MT5 top toolbar, click **Algo Trading** (the icon must turn green with a play symbol).
   - Go to **Tools > Options > Expert Advisors**:
     - Check *"Allow Algorithmic Trading"*.
3. **Install the News Calendar Exporter:**
   - In MT5, click **File > Open Data Folder**.
   - Note down this path (e.g. `C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\<TerminalID>`).
   - Run the automated installer:
     ```powershell
     .\backend\.venv\Scripts\python.exe scripts/install_mt5_calendar.py --terminal-data-dir "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\<TerminalID>"
     ```
   - In MT5 Navigator pane, right-click **Expert Advisors > Refresh**.
   - Open any single liquid chart (e.g. `EURUSD` M1) and drag **`QROS/QROSCalendarExport`** onto it.
   - *Confirmation:* The chart comment in the top-left will display:
     `QROS built-in calendar: complete | Events: XX | Errors: 0`.

---

### Step 4: Configure Calendar Path in `.env`
Open `C:\QROS-PROP\.env` and verify that `QROS_NEWS_CALENDAR_PATH` points to the exported `calendar.json`:
```dotenv
QROS_NEWS_FILTER_ENABLED=true
QROS_NEWS_CALENDAR_PATH=C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/<TerminalID>/MQL5/Files/QROS/calendar.json
```

---

### Step 5: Check System Readiness
Run the institutional readiness audit:
```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -c "
from qros.db.session import session_factory, session_scope
from qros.config.settings import Settings
from qros.services.readiness import readiness
s = Settings()
factory = session_factory(s.database_url)
with session_scope(factory) as db:
    r = readiness(db, s)
    for c in r.get('checks', []):
        tag = '[PASS]' if c['passed'] else '[BLOCKED]'
        print(f'{tag:9} {c[\"name\"]:32} : {c[\"detail\"]}')
"
```
Once MT5 is running and logged in, all prerequisite connectivity and rule gates will report **`[PASS]`**.

---

### Step 6: Start All Background Services
Double-click **`START_QROS.bat`** (or run `.\deployment\start_services.ps1`).

This launches under continuous PowerShell supervision:
1. **API Gateway & Web Dashboard** (`run_backend.ps1` on port 8000).
2. **Data Calibration Worker** (`run_data.ps1` syncing 5 major pairs and managing ATRs).
3. **Core Risk & Execution Engine** (`run_executor.ps1` enforcing the Anti-Ruin Dynamic Governor).

To cleanly shut down services, double-click **`STOP_QROS.bat`** (or run `.\deployment\stop_services.ps1`).

---

## 3. Web Dashboard & Private Access

- **Dashboard URL:** Open Chrome/Edge and visit: `http://127.0.0.1:8000/`
- **Authentication:**
  - Login Field: **API bearer token** (No username).
  - Open `DASHBOARD_LOGIN_PRIVATE.txt` or read `QROS_API_TOKEN` from `.env`.
  - Paste your 64-character token and click **Connect to desk**.

---

## 4. Scaling the Account from Payouts

QROS is built on complete percentage dynamism. When you progress from your \$5,000 account to higher tiers using payout profits, **no code modifications are required**.

Simply run the binding command with your new balance:

```powershell
# Upgrading to $10,000 Account:
.\backend\.venv\Scripts\python.exe scripts/bind_active_account.py --balance 10000

# Upgrading to $25,000 Account:
.\backend\.venv\Scripts\python.exe scripts/bind_active_account.py --balance 25000

# Upgrading to $50,000 Account:
.\backend\.venv\Scripts\python.exe scripts/bind_active_account.py --balance 50000
```

The system will dynamically recalculate all daily loss anchors, the 2.25% anti-ruin drawdown thresholds, and strategy lot sizing.

---

## 5. Daily Operating Checklist

1. [ ] **VPS Boot / Restart:** MT5 starts automatically; Algo Trading button is active (green).
2. [ ] **Calendar Exporter:** `calendar.json` is being updated every 30 seconds by the MT5 EA.
3. [ ] **Supervisors Active:** API, Data Worker, and Executor command windows are running.
4. [ ] **Heartbeats & Risk:** Dashboard indicates `risk_within_limits: PASS` and `news_calendar_coverage: PASS`.
5. [ ] **Audit Trail:** Backups are written daily to `C:\QROS-Runtime\backups\`.
