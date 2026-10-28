# Commissioning â€” 2026-10-23

Installed into `C:\Users\adhik\.gemini\antigravity-ide\scratch\qros-prop`.
Previous files and database are recoverable under
`.implementation-backups/20261023-231323`. The copied SQLite snapshot passed
integrity checking; 130 runtime files matched the verified build at handover.
Subsequent deployment corrections use the API factory entry point and preserve
native stderr under Windows PowerShell 5.

## Verified implementation

- Backend suite: **220 passed, two warnings** (Starlette dependency deprecation;
  SciPy precision warning for a nearly constant synthetic fixture).
- Frontend: TypeScript and Vite production build passed.
- Installed database: seven completed exploratory jobs, 42 experiments,
  zero submitted order-ledger entries and zero trade-journal entries.
- Audit chain verified after transfer.
- Real FTMO demo monitoring resumed with a fresh account snapshot and a verified
  current +10,800-second platform clock offset.
- Owner-confirmed **2-Step Free Trial**, USD 50,000 initial capital. Applicable
  profile and source references are in `FTMO_ACCOUNT_RULES.md`.
- Initial capture: 42 immutable bar archives across seven instruments and six
  timeframes, plus seven bid/ask tick archives; no initial capture errors.
- All 42 exploratory research candidates are ineligible for deployment. The final
  holdout was not consumed, and no strategies were promoted or activated.

## Runtime and operations

Production dashboard: http://127.0.0.1:8000/ . It uses the private token in `.env`.
API, executor, research and hourly read-only data worker have separate Windows
supervisor scripts. Logs are in `var/logs`; authenticated runtime checks are
written to `var/readiness/acceptance.json` by `scripts/verify_installation.py`.
That report records observed failures as failures; process existence alone is
not a successful health check. No reboot Scheduled Tasks or remote VPS deployment
have been installed. Online SQLite backup and restore tooling is available.

Trading mode remains **OFF / STOPPED**, with no selected strategies, host order
execution disabled and live trading disabled. No broker orders were submitted.
Telegram remains deferred.

## Remaining operational evidence

Live-market readiness has not been established. Remaining gates include a verified
firm-reset balance anchor, verified trial expiry, historical timestamp/session and
cost evidence, runtime-equivalent validated strategies, required owner approvals,
and measured forward paper/demo execution. The commission setting is an assumption,
not a verified fee schedule. Current clock calibration does not certify historical
DST mappings. Passing software tests cannot establish profitability or replace
forward observations.

## Final installed runtime acceptance

At 2026-10-23 17:57 UTC, dashboard HTML, authentication and system readiness
endpoints all returned HTTP 200. Executor, research and data heartbeats were less
than two seconds old, with no reported error. Broker reconciliation was clean;
the audit chain verified across 35 entries. The first installed hourly capture
completed 42 bar archives and seven tick archives with zero errors; its next
capture is scheduled by the running worker. This is capture success, not historical
coverage or timestamp certification. Raw coverage remains unverified.

Readiness reports three current blockers: verified firm-reset anchor, host
execution permission, and approved validated strategy. Mode is OFF / STOPPED.
No orders or trades were submitted. Browser automation timed out; frontend build
and HTTP delivery passed, but the final installed visual check remains incomplete.
See `var/readiness/acceptance_summary.json` for the compact observed result and
`acceptance.json` for its full evidence.
