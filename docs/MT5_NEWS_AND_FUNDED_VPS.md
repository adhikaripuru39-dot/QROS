# MT5 calendar and funded FTMO Standard deployment

## Current decision: Windows VPS staging only

Update 2026-10-24: the native calendar exporter is now attached and actual fresh,
complete snapshots with zero query errors have been verified. The owner changed
the immediate target to local FTMO 2-Step demo forward testing before VPS
migration. See [the demo commissioning record](DEMO_FORWARD_TEST.md). The funded
limitations below still apply; references to pending attachment describe the
earlier commissioning state, superseded by this update.

The intended funded account type is **Standard**, confirmed by the owner on
2026-10-24. The connected account is still a $50,000 2-Step Free Trial. Its
evaluation exemptions are not funded Standard permissions. The connected
account and active profile have not been switched to funded. Live remains
disabled; the separately documented demo experiment has host execution enabled.
An MT5 demo/real flag alone does not establish FTMO contractual programme status.

The application includes Windows supervisors, pause-on-restart recovery, process
locks, authentication and SQLite backup tools. Deploy to a normal Windows VPS
supporting the terminal and Python processes in the same logged-in user session.
No remote host was configured or commissioned in this task. Validate account
binding, network/TLS access, restore and reboot recovery on the destination.
Do not expose the loopback API directly to the public internet.

Funded activation still requires verified funded rules and capital, validated
runtime-equivalent strategies, historical cost/time evidence, paper/demo forward
execution, owner approval, fresh risk observations, funded news/holding controls,
and a tested VPS recovery/backup procedure. Passing unit tests is not funded approval.

## Built-in MT5 calendar bridge

MT5's official Python integration has no calendar function. The supplied
`mt5/QROSCalendarExport.mq5` EA reads `CalendarValueHistory` in the installed
terminal and exports a local snapshot every 30 seconds. It contains no trade
functions, WebRequest, DLL imports or credentials.

Install on another Windows host:

```powershell
./backend/.venv/Scripts/python.exe -B scripts/install_mt5_calendar.py --terminal-data-dir "C:/.../MetaQuotes/Terminal/<terminal-id>"
```

Select the data folder for the actual FTMO installation, not another MT5 terminal.
In MT5 Navigator, refresh Expert Advisors, open a dedicated chart and attach
`QROS/QROSCalendarExport`. Do not replace an existing trading EA. The exporter
does not require enabling DLLs or granting it trading permission.

Set these private host configuration values and restart QROS:

```dotenv
QROS_NEWS_FILTER_ENABLED=true
QROS_NEWS_CALENDAR_PATH=C:/.../MQL5/Files/QROS/calendar.json
QROS_NEWS_MINUTES_BEFORE=5
QROS_NEWS_MINUTES_AFTER=5
QROS_NEWS_MIN_IMPORTANCE=2
QROS_NEWS_MAX_AGE_SECONDS=120
```

Keep the chart/exporter running. Risk Center and `/api/system/news` report its
status. The local exporter compiled with zero errors and warnings. The owner
attached it on 2026-10-24; genuine fresh complete snapshots have now been
verified. The filter fails closed if the exporter stops or coverage becomes invalid.

## Filter behaviour and limits

- New entries are checked again at the central execution boundary, even when
  the evaluation profile itself has no firm news restriction. The stricter of
  the internal and firm buffers applies. Importance 2 includes moderate and high
  events. Currency coverage includes USD/EUR/GBP/JPY/CHF/CAD/AUD; gold is exposed
  to USD news. Unsupported currencies are blocked pending coverage.
- Native calendar dates are in trade-server time. Blackouts compare events on
  that same axis; snapshots use UTC only for age checking. Wrong server/offset,
  failed/partial queries, unresolved metadata, missing currencies and stale or
  future-dated snapshots block entries. Unknown event times block the affected
  server day. Future UTC display estimates do not certify a DST schedule.
- This is a conservative internal entry filter, not a verified mapping of
  MetaQuotes events to FTMO's selected restricted announcements. That mapping
  must be checked against FTMO's current calendar on the destination account.
- FTMO Standard restrictions include pending-order and SL/TP execution within
  the restricted window. This implementation does not flatten holdings or cancel
  pending orders ahead of news, and cannot guarantee stop/target fills will not
  occur. Funded news compliance remains **unverified**. Protective stops are
  never removed to bypass a news restriction.
- Platform VPS features must not be assumed to host QROS's external Python/API
  processes. Exporter/chart persistence and timezone behaviour must be included
  in the destination host's restart test.

Primary sources checked 2026-10-24:

- https://www.mql5.com/en/docs/python_metatrader5
- https://www.mql5.com/en/docs/calendar
- https://www.mql5.com/en/docs/calendar/calendarvaluehistory
- https://www.mql5.com/en/docs/constants/structures/mqlcalendar
- https://ftmo.com/en/faq/can-i-trade-news/


## Local verification — 2026-10-24

243 backend tests passed (two dependency/synthetic-fixture warnings); the
TypeScript/Vite production build passed. Installed MQL5 source matches the
project source and compiled with zero errors/warnings. All deployment PowerShell
scripts parse. The running authenticated news endpoint reports enabled filtering
with invalid coverage while no export exists; readiness correctly includes the
news-coverage blocker. The trial account binding passes and rejects different
FTMO identities in tests. Audit chain verification passed; order/trade counts
remain zero. The source parser and executable pipeline tests use isolated
calendar fixtures; no genuine terminal calendar export was claimed.

Evidence: `var/readiness/mt5_news_acceptance.json` and
`var/readiness/calendar_compile.log`. The future funded Standard programme and
capital remain unverified. No VPS or funded account was activated.
