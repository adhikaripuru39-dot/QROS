# QROS - Stage 10 Robustness Testing Compliance Checklist

Run **G0 before starting any task**. Self-attest and record results in the decision log.

## G0 - Do not proceed (blocking)
Until the Stage 10 robustness rules are approved, the following are **forbidden** and must halt work:

- [ ] Do not accept any result on the basis of a single sample, parameter setting, or market regime.
- [ ] Do not build or modify any robustness, statistics, research, feature, hypothesis, strategy, backtest, or execution code.
- [ ] Do not run uncontrolled backtesting, stress testing, or any execution work.
- [ ] Do not skip or relax any of the five false-edge diagnostics (Part 10 §2).
- [ ] Do not promote a result that has not passed the robustness suite (R10-01..R10-06).
- [ ] Do not claim ratification, approval, or production readiness.

> If any checkbox would be violated, **stop** and report the blocker.

## Pre-task
- [ ] Task is limited to robustness-testing **specification** (Parts 1-10); no implementation.
- [ ] Source governing sections cited (Part, section, diagnostic/rule id).
- [ ] Any threshold cited matches `STAGE_10_ROBUSTNESS_MAP.md` / handbook literal (ADR-001).
- [ ] Constitution still treated as draft governance.

## During-task
- [ ] No prohibited work executed (see G0).
- [ ] Each robustness rule cites its governing source (Part 10, Part 2, Part 7, Part 8).
- [ ] The five false-edge diagnostics are all specified; none is omitted.
- [ ] Only specification artifacts described — no execution logic.

## Post-task
- [ ] Outputs match the charter, scope, and robustness map; all traceable.
- [ ] No approval or production-readiness claims made.
- [ ] Decision log updated with the Stage 10 result.

## Sign-off
- Owner: ____________
- Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
