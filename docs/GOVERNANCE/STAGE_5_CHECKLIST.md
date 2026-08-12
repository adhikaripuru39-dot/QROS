# QROS - Stage 5 Hypothesis Management Compliance Checklist

Run **G0 before starting any task**. Self-attest and record results in the decision log.

## G0 - Do not proceed (blocking)
Until the Stage 5 hypothesis rules are approved, the following are **forbidden** and must halt work:

- [ ] Do not perform feature expansion, edge discovery, backtesting, or execution of any kind.
- [ ] Do not build or modify any hypothesis, feature, strategy, backtest, or execution code.
- [ ] Do not test, train, or advance any hypothesis without registration, SHA-256 lock, and pre-testing approval.
- [ ] Do not modify a locked hypothesis to fit results.
- [ ] Do not relax any eligibility or approval criterion (H5-01..H5-07) to force a hypothesis forward.
- [ ] Do not claim ratification, approval, or production readiness.

> If any checkbox would be violated, **stop** and report the blocker.

## Pre-task
- [ ] Task is limited to hypothesis **specification** (Parts 1-5); no implementation.
- [ ] Source governing sections cited (Part, section, field/rule id).
- [ ] Any threshold cited matches `STAGE_5_HYPOTHESIS_MAP.md` / handbook literal (ADR-001).
- [ ] Constitution still treated as draft governance.

## During-task
- [ ] No prohibited work executed (see G0).
- [ ] All 22 fields (HYP-01..22) are accounted for when a hypothesis is described.
- [ ] Feature/data references point only to approved Stage 4 features and Stage 3 quality snapshots.
- [ ] No locked-hypothesis modification; no retroactive criterion adjustment.

## Post-task
- [ ] Outputs match the charter, scope, and hypothesis map; all traceable.
- [ ] No approval or production-readiness claims made.
- [ ] Decision log updated with the Stage 5 result.

## Sign-off
- Owner: ____________
- Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
