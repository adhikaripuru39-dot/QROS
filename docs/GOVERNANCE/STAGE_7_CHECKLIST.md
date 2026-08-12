# QROS - Stage 7 Research Pipeline Compliance Checklist

Run **G0 before starting any task**. Self-attest and record results in the decision log.

## G0 - Do not proceed (blocking)
Until the Stage 7 pipeline rules are approved, the following are **forbidden** and must halt work:

- [ ] Do not implement or develop any strategy outside the governed pipeline.
- [ ] Do not run backtesting beyond governed research, and do not perform any execution work.
- [ ] Do not build or modify any research-pipeline, feature, hypothesis, strategy, backtest, or execution code.
- [ ] Do not advance any stage without its mandatory gate passing and sign-off.
- [ ] Do not skip a stage or relax a quality gate ("no shortcuts").
- [ ] Do not claim ratification, approval, or production readiness.

> If any checkbox would be violated, **stop** and report the blocker.

## Pre-task
- [ ] Task is limited to research-pipeline **specification** (Parts 1-7); no implementation.
- [ ] Source governing sections cited (Part, section, stage/rule id).
- [ ] Any threshold cited matches `STAGE_7_PIPELINE_MAP.md` / handbook literal (ADR-001).
- [ ] Constitution still treated as draft governance.

## During-task
- [ ] No prohibited work executed (see G0).
- [ ] Stages referenced are in the correct linear order with their gate owner.
- [ ] No gate value relaxed; failure handling follows the halt-and-log protocol.
- [ ] Only specification/research artifacts described — no execution logic.

## Post-task
- [ ] Outputs match the charter, scope, and pipeline map; all traceable.
- [ ] No approval or production-readiness claims made.
- [ ] Decision log updated with the Stage 7 result.

## Sign-off
- Owner: ____________
- Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
