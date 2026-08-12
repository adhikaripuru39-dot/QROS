# QROS - Stage 4 Feature Engineering Scope

## Stage 4 objective
Define how QROS turns approved, quality-checked data into feature **specifications** without leaking future information or drifting into hypothesis or strategy work. Specification-only; no implementation.

## In scope
- Definition of an approved feature in QROS (see `STAGE_4_CHARTER.md` §3).
- Approved feature categories and allowed transformations (Part 4 taxonomy).
- Forbidden transformations (leakage-producing or out-of-taxonomy).
- Stationarity and normalization expectations (ADF p, Z-score/percentile-rank, fracdiff).
- Leakage and look-ahead prevention; rolling-window conventions.
- Target/label separation.
- Provenance and reproducibility requirements.
- Approval thresholds and blocking conditions (F4-09).

## Out of scope
- Feature, model, or research implementation code.
- Hypothesis registration or edge claims.
- Model training, backtesting, walk-forward validation, or live execution.
- Strategy or execution logic.
- Any code of any kind.

## Inputs
- Stage 1 Governance Lock, Stage 2 Data Foundation, Stage 3 Data Quality packages.
- QROS Constitution (draft) and Founding Governance Documents.
- Master Handbook Parts 1-4.
- Project State reference-only note (`.claude/`, `_extracted/`, `scratch/`, `trading_engine/`).

## Outputs
- `STAGE_4_CHARTER.md`
- `STAGE_4_CHECKLIST.md`
- `STAGE_4_SCOPE.md`
- `STAGE_4_FEATURE_MAP.md`

## Feature rules (fixed by this stage)
F4-01 approved categories · F4-02 stationarity (ADF p<0.05) · F4-03 normalization · F4-04 no global fitting · F4-05 no price interpolation · F4-06 rolling-window conventions · F4-07 target/label separation · F4-08 provenance & reproducibility · F4-09 approval thresholds.
All are defined with thresholds and blockers in `STAGE_4_FEATURE_MAP.md`; none may be relaxed.

## Exit condition
The feature-rule set is approved as a specification-only baseline. An approved, provenance-recorded feature set (traceable to Stage 3 quality snapshots, passing F4-01..F4-09) is ready to be handed to the next governed stage for controlled implementation.
