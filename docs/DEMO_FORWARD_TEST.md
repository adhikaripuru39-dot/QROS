# Local FTMO broker demo forward testing

The owner authorized direct MT5 forward testing on 2026-10-24. This deployment
uses the reviewed $50k FTMO 2-Step Free Trial account, not a funded account.
Telegram remains deferred. No remote VPS has been deployed.

## Execution permission

Five library baselines have the explicit `DEMO_TESTING` status. They are
unvalidated experiments, not `DEMO_APPROVED` or profitable-strategy claims.
Their previous ineligible research reports remain unchanged. Permission binds
each runtime/hypothesis, implementation hash, firm and exact demo account and
expires seven days after authorization. No automatic renewal or transition to
live is available. Code/runtime/account changes require a new review.

Host order execution is enabled, host Live permission remains disabled, and
the central execution pipeline still enforces genuine quotes, broker clock,
verified daily anchor, news freshness, account binding, reconciliation,
protective stops, margin, exposure, session and duplicate-order checks.

Limits: 0.05% of the smaller balance/equity per trade (about $25 at $50k),
one open position, six broker entries per day, 0.1% aggregate stop risk,
0.5% daily/session loss stop and 2% internal total stop. Stop risk is an
estimate including configured adverse costs; gaps can exceed it. Commission
remains an explicit conservative model assumption until actual costs are
observed. Demo results cannot establish funded/live profitability.

## Calendar

The native MT5 calendar exporter is attached and genuine snapshots were
verified on 2026-10-24: complete, zero query errors, 257 calendar values and
valid currency coverage for all seven configured instruments. Its 30-second
timer must keep running. New entries block for missing/stale coverage or
moderate/high importance events within five minutes before/after. This remains
an entry filter with the funded Standard limitations documented separately.

## Starting and recovery

In Trading Control, `Arm demo when ready` records a one-time owner instruction
to start only when every demo readiness check passes. This allows a closed
weekend market to become ready without weakening quote/history checks. The
same action is available through authenticated `arm_demo` control commands.
Read `demo_forward_arm.pending` in control state to distinguish waiting from
running. Merely selecting Demo mode does not start entries.

Manual control commands, expiry, changed account/selection, a halt or an
executor restart cancel the pending arm. Once consumed it does not repeatedly
resume after disconnects or risk halts. After recovery, inspect reconciliation,
calendar and positions, then explicitly arm again or start when ready.

Four current-user interactive logon tasks (`QROS-backend`, `QROS-executor`,
`QROS-worker`, `QROS-data`) are installed. Supervisors recover failed processes.
They do not sign in to Windows or MT5; keep the same logged-in user session.
The MT5 terminal/profile and exporter must remain available. A full Windows
reboot/login test has not been performed.

`deployment/backup.ps1` creates integrity-checked online SQLite copies plus
configuration, excluding secrets. `scripts/verify_recovery.py` restored a real
backup to an isolated broker-free database, verified its audit chain and
confirmed that RUNNING recovers as PAUSED_ENTRIES without creating orders.
Do not replace the production database while a capable executor is running.

## Weekly review

Use the existing Monday-based Asia/Katmandu weekly reports in Strategy Lab.
Select Demo to review actual broker fills, rejects, commissions, slippage and
net results separately from modeled research. Review execution failures and
recovery behavior even if there are no fills. Renew permission only through
an explicit reviewed commissioning step; fork changed strategy parameters so
their future results retain separate provenance.

A first genuine MT5 fill and completed broker-deal reconciliation remain
open-market acceptance criteria before VPS migration. A Saturday calendar
snapshot and software tests do not prove those outcomes.

The local process recovery drill also terminated the owned executor child under
its existing supervisor. It recovered with a different PID, entries paused and
the pending demo arm explicitly cancelled. This was verified through the live
API before the owner-authorized demo experiment was re-armed. Evidence:
`var/readiness/process_recovery_acceptance.json`. No broker order was sent by
the recovery drill. Permission expires 2026-10-31 at about 09:34 Asia/Katmandu.

Final verification: 261 backend tests passed, with two dependency/synthetic-data
warnings; the TypeScript/Vite production build passed. The live API verified
valid calendar coverage and a pending demo arm. Its remaining readiness blockers
were broker clock verification and clean deal reconciliation during the closed
weekend market. Full evidence: `var/readiness/demo_forward_acceptance.json`.
