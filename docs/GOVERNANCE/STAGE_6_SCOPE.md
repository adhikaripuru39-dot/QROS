# QROS - Stage 6 Hypothesis Generation Scope

## Stage 6 objective
Define how QROS **generates candidate hypotheses from approved data and approved features** without turning them into tested strategies. Specification-only; no implementation.

## In scope
- Definition of a hypothesis candidate in QROS (see `STAGE_6_CHARTER.md` §3).
- Allowed and forbidden generation sources.
- Economic rationale and falsifiability requirements.
- Anomaly / behavioral mechanic categories (the 6 documented; MECH-07..15 as empty amendment-gated slots).
- Regime-awareness expectations.
- Candidate validity and blocking rules.
- Hypothesis vs tested-strategy distinction.

## Out of scope
- Hypothesis, feature, strategy, or execution implementation code.
- Hypothesis testing, model training, backtesting, or live execution.
- Edge claims or strategy claims.
- Feature engineering beyond referencing approved feature dependencies.
- Any code of any kind.

## Inputs
- Stage 1-5 governance packages (lock, data foundation, data quality, feature engineering, hypothesis management).
- QROS Constitution (draft) and Founding Governance Documents.
- Master Handbook Parts 1-6.
- Project State reference-only note; ADR-003.

## Outputs
- `STAGE_6_CHARTER.md`
- `STAGE_6_CHECKLIST.md`
- `STAGE_6_SCOPE.md`
- `STAGE_6_HYPOTHESIS_GEN_MAP.md`

## Generation rules (fixed by this stage)
G6-01 valid sources · G6-02 economic rationale · G6-03 mechanic categories (6 documented) · G6-04 regime-awareness · G6-05 candidate validity · G6-06 blocking conditions · G6-07 hypothesis vs tested strategy.
All are defined with blockers in `STAGE_6_HYPOTHESIS_GEN_MAP.md`; none may be relaxed.

## Exit condition
The generation-rule set is approved as a specification-only baseline. A documented set of valid candidate hypotheses — each mechanic-grounded, rationale-bearing, regime-aware, and dependent on approved Stage 3/4 foundations — is ready to be registered and locked under Stage 5 and carried into the next governed stage.
