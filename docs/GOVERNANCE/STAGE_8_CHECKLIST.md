# QROS - Stage 8 Statistical Research Methodology Compliance Checklist

Run **G0 before starting any task**. Self-attest and record results in the decision log.

## G0 - Do not proceed (blocking)
Until the Stage 8 statistical rules are approved, the following are **forbidden** and must halt work:

- [ ] Do not implement or develop any strategy outside the governed methodology.
- [ ] Do not run uncontrolled backtesting, and do not perform any execution work.
- [ ] Do not build or modify any statistics, research, feature, hypothesis, strategy, backtest, or execution code.
- [ ] Do not promote any result toward validation without its required statistical evidence and multiple-testing correction.
- [ ] Do not relax a statistical threshold, apply retroactive approval, or engage in p-hacking.
- [ ] Do not claim ratification, approval, or production readiness.

> If any checkbox would be violated, **stop** and report the blocker.

## Pre-task
- [ ] Task is limited to statistical-methodology **specification** (Parts 1-8); no implementation.
- [ ] Source governing sections cited (Part, section, test/rule id).
- [ ] Any threshold cited matches `STAGE_8_STATISTICS_MAP.md` / handbook literal (ADR-001).
- [ ] Constitution still treated as draft governance.

## During-task
- [ ] No prohibited work executed (see G0).
- [ ] Each required test is assigned to its correct application domain (backtest acceptance, feature screening, confirmatory testing, OOS cross-validation, robustness).
- [ ] No threshold value relaxed; multiple-testing corrections applied before promotion.
- [ ] Only specification/research artifacts described — no execution logic.

## Post-task
- [ ] Outputs match the charter, scope, and statistics map; all traceable.
- [ ] No approval or production-readiness claims made.
- [ ] Decision log updated with the Stage 8 result.

## Sign-off
- Owner: ____________
- Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
