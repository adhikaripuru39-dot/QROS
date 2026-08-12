# QROS - Stage 4 Feature Engineering Compliance Checklist

Run **G0 before starting any task**. Self-attest and record results in the decision log.

## G0 - Do not proceed (blocking)
Until the Stage 4 feature rules are approved, the following are **forbidden** and must halt work:

- [ ] Do not perform hypothesis generation, edge discovery, backtesting, or execution of any kind.
- [ ] Do not build or modify any feature, model, research, backtest, or execution code.
- [ ] Do not train any model or run any live trading.
- [ ] Do not register any hypothesis or make any edge claim.
- [ ] Do not approve any feature set unless traceable to the approved data foundation and Stage 3 quality rules.
- [ ] Do not relax any feature threshold (F4-01..F4-09) to force a pass.
- [ ] Do not claim ratification, approval, or production readiness.

> If any checkbox would be violated, **stop** and report the blocker.

## Pre-task
- [ ] Task is limited to feature **specification** (Parts 1-4); no implementation.
- [ ] Source governing sections cited (Part, section, rule id).
- [ ] Any threshold cited matches `STAGE_4_FEATURE_MAP.md` / handbook literal (ADR-001).
- [ ] Constitution still treated as draft governance.

## During-task
- [ ] No prohibited work executed (see G0).
- [ ] Approved feature categories only (taxonomy); anything else flagged for amendment.
- [ ] No global/full-sample fitting; all parameters backward-looking.
- [ ] No target-derived quantity enters feature computation (target/label separated).
- [ ] Every feature tied to an approved Stage 3 quality snapshot.

## Post-task
- [ ] Outputs match the charter, scope, and feature map; all traceable.
- [ ] No approval or production-readiness claims made.
- [ ] Decision log updated with the Stage 4 result.

## Sign-off
- Owner: ____________
- Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
