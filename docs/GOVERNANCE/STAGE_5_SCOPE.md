# QROS - Stage 5 Hypothesis Management Scope

## Stage 5 objective
Define how QROS **registers, locks, and governs hypotheses** before any research or testing begins. Specification-only; no implementation.

## In scope
- Definition of a valid QROS hypothesis (see `STAGE_5_CHARTER.md` §3).
- Hypothesis identity and naming convention (HYP-01).
- The full 22-field hypothesis record (HYP-01..HYP-22).
- Economic rationale and falsifiability requirements.
- Pre-registration and SHA-256 locking mechanism.
- Ownership and approval status (pre-testing approval).
- Eligibility-for-testing and blocking rules.

## Out of scope
- Hypothesis, feature, strategy, or execution implementation code.
- Hypothesis testing, model training, backtesting, or live execution.
- Edge claims or strategy logic.
- Feature work beyond documenting hypothesis inputs and dependencies.
- Any code of any kind.

## Inputs
- Stage 1-4 governance packages (lock, data foundation, data quality, feature engineering).
- QROS Constitution (draft) and Founding Governance Documents.
- Master Handbook Parts 1-5.
- Project State reference-only note.

## Outputs
- `STAGE_5_CHARTER.md`
- `STAGE_5_CHECKLIST.md`
- `STAGE_5_SCOPE.md`
- `STAGE_5_HYPOTHESIS_MAP.md`

## Hypothesis rules (fixed by this stage)
H5-01 identity/naming · H5-02 full 22-field record · H5-03 rationale & falsifiability · H5-04 pre-registration & SHA-256 lock · H5-05 ownership & approval · H5-06 eligibility for testing · H5-07 blocking conditions.
All are defined with fields and blockers in `STAGE_5_HYPOTHESIS_MAP.md`; none may be relaxed.

## Exit condition
The hypothesis-rule set is approved as a specification-only baseline. Registered, SHA-256-locked, pre-testing-approved hypothesis(es) — with dependencies on approved Stage 3 data and Stage 4 features — are ready to be handed to the next governed stage for controlled research.
