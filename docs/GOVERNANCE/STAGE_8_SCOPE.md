# QROS - Stage 8 Statistical Research Methodology Scope

## Stage 8 objective
Define the **statistical methodology rules** that govern how QROS tests hypotheses and research results — without p-hacking, threshold drift, or retroactive approval. Specification-only; no implementation.

## In scope
- Definition of statistical methodology in QROS (see `STAGE_8_CHARTER.md` §3).
- Required statistical tests and where they apply (DSR, FDR-BH, FWER-Holm, CPCV, stationary bootstrap, permutation tests; ST8-01).
- Multiple-testing control, including trial-count tracking through the Experiment Registry (ST8-02).
- False-discovery and family-wise error rules (ST8-03).
- Out-of-sample and cross-validation expectations (CPCV purging/embargo, walk-forward OOS; ST8-04).
- Minimum evidence thresholds (ST8-05).
- Robustness and sensitivity requirements (ST8-06).
- What blocks a result from being promoted (ST8-07).
- Conditions that must be met before a result can move toward validation.

## Out of scope
- Statistics, research, feature, hypothesis, strategy, backtest, or execution implementation code.
- Live trading, order dispatch, or execution code.
- Strategy development outside the governed methodology.
- Uncontrolled backtesting or p-hacking.
- Research execution beyond specifying the statistical rules that govern it.
- Any code of any kind.

## Inputs
- Stage 1-7 governance packages (governance lock, data foundation, data quality, feature engineering, hypothesis management, hypothesis generation, research pipeline).
- QROS Constitution (draft) and Founding Governance Documents.
- Master Handbook Parts 1-8.
- Project State reference-only note; ADR-001.

## Outputs
- `STAGE_8_CHARTER.md`
- `STAGE_8_CHECKLIST.md`
- `STAGE_8_SCOPE.md`
- `STAGE_8_STATISTICS_MAP.md`

## Statistical rules (fixed by this stage)
ST8-01 required tests & application domains · ST8-02 multiple-testing control · ST8-03 FDR/FWER rules · ST8-04 OOS & cross-validation · ST8-05 minimum evidence thresholds · ST8-06 robustness & sensitivity · ST8-07 promotion blockers.
All are defined with mandatory gates and blockers in `STAGE_8_STATISTICS_MAP.md`; none may be relaxed (Part 8 mandate; Part 7 Quality Gate Failure Rule; ADR-001).

## Exit condition
The statistical-rule set is approved as a specification-only baseline. Required tests, corrections, OOS/CV expectations, and minimum evidence thresholds are fixed; the conditions that must hold before any result moves toward validation are specified (see `STAGE_8_STATISTICS_MAP.md`, final sections); and the artifacts required before Stage 9 may begin are specified. No result is promoted, no hypothesis is validated, and no threshold is relaxed outside these rules.
