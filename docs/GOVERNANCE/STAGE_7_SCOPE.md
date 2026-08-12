# QROS - Stage 7 Research Pipeline Scope

## Stage 7 objective
Define the **linear research workflow** that turns approved hypotheses and approved features into **governed research work**, with explicit gates and no shortcuts. Specification-only; no implementation.

## In scope
- Definition of the research pipeline in QROS (see `STAGE_7_CHARTER.md` §3).
- Stage order and dependencies (the 15-stage linear workflow; P7-01).
- Required approvals and sign-offs per stage (P7-02).
- Gate failures and rollback conditions, including the halt-and-log protocol (P7-03).
- Research execution boundaries — where backtesting/walk-forward may and may not run (P7-04).
- Allowed artifacts per stage (P7-05).
- What blocks progression to validation or approval (P7-06).
- Mandatory stage gates and how a failed gate is handled.
- The do-not-proceed list blocking strategy implementation, backtesting beyond governed research, and execution work.

## Out of scope
- Research-pipeline, feature, hypothesis, strategy, backtest, or execution implementation code.
- Live trading, order dispatch, or execution code.
- Strategy development outside the governed pipeline.
- Backtesting beyond governed research.
- Hypothesis, feature, or model work beyond referencing approved Stage 4/5/6 inputs.
- Any code of any kind.

## Inputs
- Stage 1-6 governance packages (governance lock, data foundation, data quality, feature engineering, hypothesis management, hypothesis generation).
- QROS Constitution (draft) and Founding Governance Documents.
- Master Handbook Parts 1-7.
- Project State reference-only note; ADR-001.

## Outputs
- `STAGE_7_CHARTER.md`
- `STAGE_7_CHECKLIST.md`
- `STAGE_7_SCOPE.md`
- `STAGE_7_PIPELINE_MAP.md`

## Pipeline rules (fixed by this stage)
P7-01 stage order & dependencies · P7-02 approvals & sign-offs · P7-03 gate failures & rollback · P7-04 research execution boundaries · P7-05 allowed artifacts · P7-06 progression blockers.
All are defined with mandatory gates and blockers in `STAGE_7_PIPELINE_MAP.md`; none may be relaxed (Part 7 §2; ADR-001).

## Exit condition
The pipeline-rule set is approved as a specification-only baseline. Approved, registered hypotheses (Stage 5/6) and approved features (Stage 4) are queued into the governed 15-stage workflow; the gate-failure / rollback protocol is in place; the artifacts required before Stage 8 may begin are specified (see `STAGE_7_PIPELINE_MAP.md`, final section). No research, backtest, or execution work proceeds outside these rules.
