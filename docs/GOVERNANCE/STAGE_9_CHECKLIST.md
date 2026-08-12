# QROS - Stage 9 Experiment Tracking Compliance Checklist

Run **G0 before starting any task**. Self-attest and record results in the decision log.

## G0 - Do not proceed (blocking)
Until the Stage 9 tracking rules are approved, the following are **forbidden** and must halt work:

- [ ] Do not run untracked experimentation, hide a trial, or omit any failed attempt from the record.
- [ ] Do not edit, back-date, or delete experiment records after the fact.
- [ ] Do not build or modify any tracking, statistics, research, feature, hypothesis, strategy, backtest, or execution code.
- [ ] Do not run uncontrolled backtesting, and do not perform any execution work.
- [ ] Do not accept any experiment record that is incomplete or missing its dataset/git/hypothesis linkage.
- [ ] Do not claim ratification, approval, or production readiness.

> If any checkbox would be violated, **stop** and report the blocker.

## Pre-task
- [ ] Task is limited to experiment-tracking **specification** (Parts 1-9); no implementation.
- [ ] Source governing sections cited (Part, section, field/rule id).
- [ ] Any field or linkage cited matches `STAGE_9_TRACKING_MAP.md` / handbook literal (ADR-001).
- [ ] Constitution still treated as draft governance.

## During-task
- [ ] No prohibited work executed (see G0).
- [ ] Every EXP field defined from the **17-field record** (EXP-01..EXP-17); no invented or dropped fields.
- [ ] Linkages (dataset SHA-256, git commit, feature version, hypothesis ID) specified.
- [ ] Only specification artifacts described — no execution logic.

## Post-task
- [ ] Outputs match the charter, scope, and tracking map; all traceable.
- [ ] No approval or production-readiness claims made.
- [ ] Decision log updated with the Stage 9 result.

## Sign-off
- Owner: ____________
- Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
