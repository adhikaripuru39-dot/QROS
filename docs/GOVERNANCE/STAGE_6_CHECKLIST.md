# QROS - Stage 6 Hypothesis Generation Compliance Checklist

Run **G0 before starting any task**. Self-attest and record results in the decision log.

## G0 - Do not proceed (blocking)
Until the Stage 6 generation rules are approved, the following are **forbidden** and must halt work:

- [ ] Do not perform edge discovery, hypothesis testing, backtesting, or execution of any kind.
- [ ] Do not build or modify any hypothesis, feature, strategy, backtest, or execution code.
- [ ] Do not assert any edge or strategy claim on any candidate.
- [ ] Do not advance any candidate to testing without Stage 5 registration, lock, and pre-testing approval.
- [ ] Do not invent or use an undocumented anomaly mechanic (MECH-07..15) without an amendment.
- [ ] Do not claim ratification, approval, or production readiness.

> If any checkbox would be violated, **stop** and report the blocker.

## Pre-task
- [ ] Task is limited to hypothesis **generation specification** (Parts 1-6); no implementation.
- [ ] Source governing sections cited (Part, section, mechanic/rule id).
- [ ] Any mechanic cited is one of the **6 documented** (or flagged for amendment per ADR-003).
- [ ] Constitution still treated as draft governance.

## During-task
- [ ] No prohibited work executed (see G0).
- [ ] Each candidate names its mechanic, rationale, regime, and approved Stage 3/4 dependencies.
- [ ] No candidate asserts performance, backtest, or edge results.
- [ ] No feature engineering performed; only approved feature dependencies referenced.

## Post-task
- [ ] Outputs match the charter, scope, and generation map; all traceable.
- [ ] No approval or production-readiness claims made.
- [ ] Decision log updated with the Stage 6 result.

## Sign-off
- Owner: ____________
- Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
