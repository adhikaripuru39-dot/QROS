# QROS - Stage 3 Data Quality Compliance Checklist

Run **G0 before starting any task**. Self-attest and record results in the decision log.

## G0 - Do not proceed (blocking)
Until the Stage 3 quality rules are approved, the following are **forbidden** and must halt work:

- [ ] Do not build or modify any pipeline, feature, hypothesis, strategy, backtest, or execution code.
- [ ] Do not perform feature engineering, hypothesis generation, or edge discovery.
- [ ] Do not run backtests, walk-forward validation, or live execution.
- [ ] Do not promote or freeze any dataset for experimentation without approved Stage 3 quality rules.
- [ ] Do not relax any quality threshold (M3-01..M3-08) to force a dataset to pass.
- [ ] Do not claim ratification, approval, or production readiness.

> If any checkbox would be violated, **stop** and report the blocker.

## Pre-task
- [ ] Task is limited to data-quality **specification** (Parts 1-3); no implementation.
- [ ] Governing source sections are cited (Part, section, rule id).
- [ ] Any threshold cited matches `STAGE_3_QUALITY_MAP.md` / handbook literal (ADR-001).
- [ ] Constitution still treated as draft governance.

## During-task
- [ ] No prohibited work executed (see G0).
- [ ] Mandatory checks referenced use the exact thresholds (completeness 0.05%, MAD 8.0, spread 500bps, close-recon 1bp, etc.).
- [ ] No retroactive adjustment of criteria to force a pass.
- [ ] No dataset marked approved without M3-01..M3-08 pass + DE/DGO sign-off.

## Post-task
- [ ] Outputs match the charter, scope, and quality map; all traceable.
- [ ] No approval or production-readiness claims made.
- [ ] Decision log updated with the Stage 3 result.

## Sign-off
- Owner: ____________
- Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
