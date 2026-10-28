# Strategy library and weekly reviews

Five established families are accessible in **Strategy Lab â†’ Five-strategy research
library**: channel trend following, trend pullback continuation, range mean
reversion, volatility squeeze breakout and failed-breakout reversal.

These are explicit QROS research variants, not a ranking of the world's most
profitable traders. The exact entries, default exits, capacity limitations and
primary source links appear on each template card. Broad trend-following evidence
does not prove an intraday FX/CFD variant. Indicator and trading education explains
a hypothesis; it does not establish net returns or scalability on this account.

Initial studies use EURUSD H1 trend following/pullbacks, EURUSD M15 mean reversion,
XAUUSD H1 squeeze and XAUUSD M15 failed breakouts. They start as IDEA. Baseline
research uses real archived bars with existing timestamp/cost limitations, records
development and validation results, and leaves final OOS sealed. It places no orders.

## Weekly workflow

1. Select the exact research version, Monday starting the week and execution mode.
   Weeks use Asia/Katmandu, Monday 00:00 through the following Monday, excluding
   that ending instant. A current week is labelled partial.
2. Load the report. Review net expectancy/P&L, drawdown, win-rate uncertainty,
   R-multiples, costs, trade list, order outcomes and observed signal reasons.
   Paper, demo and live logs stay separate. Research reports are separately labelled.
   No trades means no forward evidence; zero profit is not fabricated.
3. Save notes, the decision and next hypothesis. An immutable report snapshot and
   audit entry preserve exactly what was reviewed. A changed report requires refresh.
   Review decisions do not themselves change lifecycle or trading permission.
4. If justified, propose one change and fork a new version. Symbol, timeframe, ATR
   period (5â€“50), stop and target multipliers (0.5â€“10) are configurable. Template v1
   entry lookbacks/filters are fixed. Existing versions/results are preserved; the
   child starts as IDEA without inherited evidence or approvals.
5. Research the saved child. Compare both versions on development/validation data,
   record every attempted change, and reject fragile cost/small-sample improvements.
   A weekly win/loss streak alone is insufficient reason to retune. Do not repeatedly
   inspect or tune the final holdout; a reviewed frozen cohort is required by the
   existing protocol before OOS finalization.

Signal logs begin when the executor evaluates a selected, lifecycle-approved
strategy. They are deduplicated by strategy/mode/bar/reason and persist across
restarts. IDEA versions do not silently bypass execution gates for forward fills.
No automatic weekly parameter changes or trading activation are performed.

Scaling must be measured from spreads, slippage, fill reliability, financing,
portfolio correlation and drawdown. The five families overlap; USD FX pairs and
gold cannot be assumed independent. Existing risk and owner-approval gates apply.


## Installed acceptance — 2026-10-24

230 backend tests passed (two dependency/fixture warnings); the TypeScript/Vite
production build passed and the API serves the current bundle. All five initial
baseline research jobs completed and are attached to their exact saved versions.
All five weekly report endpoints passed HTTP verification, with zero forward
trades and no fabricated net P&L. The audit chain verified. No strategies were
promoted or activated; execution remains OFF. Browser automation was unavailable,
so a final visual browser check could not be completed. Acceptance evidence is
stored in `var/readiness/strategy_library_acceptance.json`.
