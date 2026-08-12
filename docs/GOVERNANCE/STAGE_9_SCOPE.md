# QROS - Stage 9 Experiment Tracking Scope

## Stage 9 objective
Define how QROS **records, traces, and preserves experiment history** so every trial is reproducible, auditable, and linked to its data, code, and approval context. Specification-only; no implementation.

## In scope
- Definition of experiment tracking in QROS (see `STAGE_9_CHARTER.md` §3).
- Required experiment-record fields (the 17-field EXP record, EXP-01..EXP-17; T9-01).
- Git-commit and dataset-snapshot linkage (T9-02).
- Seed, parameter, and environment capture (T9-03).
- Trial counting and failed-attempt logging, including the trial-count→DSR linkage (T9-04).
- Artifact retention and traceability (WORM immutable store; T9-05).
- Decision-log / registry cross-linking (T9-06).
- What blocks an experiment from being accepted (T9-07).
- What makes an experiment record complete.

## Out of scope
- Tracking, statistics, research, feature, hypothesis, strategy, backtest, or execution implementation code.
- Live trading, order dispatch, or execution code.
- Strategy development outside the governed workflow.
- Hidden or unlogged experimentation; retroactive editing of records.
- Statistical testing, backtesting, or validation execution (governed by Stages 7-8).
- Any code of any kind.

## Inputs
- Stage 1-8 governance packages (governance lock through statistical research methodology).
- QROS Constitution (draft) and Founding Governance Documents.
- Master Handbook Parts 1-9.
- Project State reference-only note; ADR-001.

## Outputs
- `STAGE_9_CHARTER.md`
- `STAGE_9_CHECKLIST.md`
- `STAGE_9_SCOPE.md`
- `STAGE_9_TRACKING_MAP.md`

## Tracking rules (fixed by this stage)
T9-01 required record fields (EXP-01..EXP-17) · T9-02 snapshot & git linkage · T9-03 seed/parameter/environment capture · T9-04 trial counting & failed-attempt logging · T9-05 artifact retention & traceability · T9-06 decision-log/registry cross-linking · T9-07 acceptance blockers.
All are defined with mandatory gates and blockers in `STAGE_9_TRACKING_MAP.md`; none may be relaxed (Part 9 mandate; ADR-001).

## Exit condition
The tracking-rule set is approved as a specification-only baseline. The mandatory 17-field record, its linkages, seed/parameter/environment capture, trial-count logging, and immutable retention are fixed; the conditions that make a record complete and the artifacts required before Stage 10 may begin are specified (see `STAGE_9_TRACKING_MAP.md`, final sections). No experiment is accepted, hidden, or retroactively edited outside these rules.
