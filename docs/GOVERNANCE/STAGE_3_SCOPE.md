# QROS - Stage 3 Data Quality Scope

## Stage 3 objective
Define how QROS validates **trust in data** before any later stage can use it. Specification-only; no implementation.

## In scope
- Definition of data quality in QROS (see `STAGE_3_CHARTER.md` §3).
- Mandatory quality checks and thresholds: completeness, timestamp integrity, duplicate detection, bad-tick suppression, missing-data handling, point-in-time / no-lookahead, provenance & correction, approval thresholds.
- Failure rules that block downstream feature, hypothesis, edge, backtest, and execution work.
- Artifacts that must exist before Stage 4 may begin.

## Out of scope
- Data pipeline logic, data engineering implementation.
- Feature engineering implementation.
- Hypothesis generation or edge discovery.
- Backtesting, walk-forward validation, or live execution.
- Strategy or execution logic.
- Any code of any kind.

## Inputs
- Stage 1 Governance Lock artifacts.
- Stage 2 Data Foundation package.
- QROS Constitution (draft) and Founding Governance Documents.
- Master Handbook Parts 1-3.

## Outputs
- `STAGE_3_CHARTER.md`
- `STAGE_3_CHECKLIST.md`
- `STAGE_3_SCOPE.md`
- `STAGE_3_QUALITY_MAP.md`

## Mandatory checks (fixed by this stage)
M3-01 completeness · M3-02 timestamp integrity · M3-03 duplicates · M3-04 bad-tick suppression · M3-05 missing-data handling · M3-06 point-in-time / no-lookahead · M3-07 provenance & correction · M3-08 approval thresholds.
All are defined with thresholds and downstream blockers in `STAGE_3_QUALITY_MAP.md`; none may be relaxed.

## Exit condition
The data-quality rule set is approved as a specification-only baseline. Approved, frozen datasets satisfying M3-01..M3-08 exist and are ready to be handed to Stage 4 (feature engineering planning) for controlled implementation.
