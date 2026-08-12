# QROS - Stage 10 Robustness Testing Scope

## Stage 10 objective
Define how QROS **performs robustness testing on governed research results** so that results are not accepted on the basis of a single fragile sample, parameter setting, or market regime. Specification-only; no implementation.

## In scope
- Definition of robustness in QROS (see `STAGE_10_CHARTER.md` §3).
- Parameter stability requirements — the ±50% pipeline gate and the ±10% curve-fitting diagnostic (R10-01).
- Sensitivity analysis expectations — stationary bootstrap and permutation tests (R10-02).
- Stress testing requirements — the five false-edge diagnostics (Part 10 §2; R10-03).
- Regime-shift and subperiod analysis — stress-period coverage, multi-decade spans, edge-type verification (R10-04).
- Sample perturbation expectations — CPCV, multi-decade backtest spans, bootstrap resampling (R10-05).
- What counts as robustness evidence (R10-06).
- What blocks a result from moving forward (R10-07).
- How failed robustness is logged and blocked.

## Out of scope
- Robustness, statistics, research, feature, hypothesis, strategy, backtest, or execution implementation code.
- Live trading, order dispatch, or execution code.
- Strategy development outside the governed workflow.
- Uncontrolled backtesting or stress testing beyond the governed pipeline.
- Walk-forward validation execution (governed by the pipeline at Stage 11).
- Any code of any kind.

## Inputs
- Stage 1-9 governance packages (governance lock through experiment tracking).
- QROS Constitution (draft) and Founding Governance Documents.
- Master Handbook Parts 1-10.
- Project State reference-only note; ADR-001.

## Outputs
- `STAGE_10_CHARTER.md`
- `STAGE_10_CHECKLIST.md`
- `STAGE_10_SCOPE.md`
- `STAGE_10_ROBUSTNESS_MAP.md`

## Robustness rules (fixed by this stage)
R10-01 parameter stability · R10-02 sensitivity analysis · R10-03 stress testing (5 false-edge diagnostics) · R10-04 regime-shift & subperiod analysis · R10-05 sample perturbation · R10-06 robustness-evidence definition · R10-07 promotion blockers.
All are defined with mandatory gates and blockers in `STAGE_10_ROBUSTNESS_MAP.md`; none may be relaxed (Part 7 §2; Part 10 mandate; ADR-001).

## Exit condition
The robustness-rule set is approved as a specification-only baseline. Parameter stability, sensitivity analysis, stress testing, regime-shift coverage, sample perturbation, and the five false-edge diagnostics are fixed; the conditions that constitute robustness evidence and the artifacts required before Stage 11 may begin are specified (see `STAGE_10_ROBUSTNESS_MAP.md`, final sections). No result is accepted on the basis of a single fragile sample, and no threshold is relaxed outside these rules.
