# QROS Decision Log

This log records governance decisions, amendments, and baseline clarifications for the QROS project.

## ADR-006 - Ratification status clarification

- Date: 2026-08-12
- Status: Open discrepancy resolved for governance purposes, not by altering the constitution text
- Context: The Constitution file in `_extracted/QROS Constitution.txt` still states `Status: Draft for Ratification`, while the Stage 1 governance package must not assume ratification unless the constitution itself is updated.
- Decision: Treat the Constitution as draft governance for all current work. Do not claim ratification, production readiness, or approval until the governing document itself is revised and explicitly ratified.
- Rationale: Stage 1 must preserve the no-skip rule and avoid retroactive approval claims. Governance text and operating state must remain consistent.
- Next action: If ratification is later desired, create a formal amendment entry and update the constitution text in a controlled governance step.

## ADR-007 - Stage 1 baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 1 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 1 charter, checklist, and stage-sequence map as the current operating baseline for future Claude Code tasks.
- Rationale: These artifacts establish the no-implementation rule, the stage order, and the do-not-proceed gate.
- Next action: Use the Stage 1 package as the mandatory pre-task check for any future work.

## ADR-008 - Stage 7 research pipeline baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 7 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 7 charter, checklist, scope, and pipeline map as the current operating baseline for research-pipeline governance.
- Rationale: These artifacts define the governed 15-stage research workflow, mandatory gates, rollback handling, and the boundary between approved hypothesis/feature inputs and research execution.
- Next action: Use the Stage 7 package as the mandatory pre-task check before any Stage 8 work is opened.

## ADR-009 - Stage 8 statistical methodology baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 8 governance artifacts exist in `docs/GOVERNANCE/` and were corrected to remove implied Bayesian-mandate language and to treat the full 17-field experiment record as a downstream dependency rather than a Stage 8 authority.
- Decision: Accept the Stage 8 charter, checklist, scope, and statistics map as the current operating baseline for statistical-methodology governance.
- Rationale: These artifacts define the governed statistical evidence rules, multiple-testing correction protocol, cross-validation expectations, robustness requirements, and promotion blockers for research results.
- Next action: Use the Stage 8 package as the mandatory pre-task check before any Stage 9 work is opened.

## ADR-010 - Stage 9 experiment tracking baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 9 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 9 charter, checklist, scope, and tracking map as the current operating baseline for experiment-tracking governance.
- Rationale: These artifacts define the governed experiment record, linkage to git commits and dataset snapshots, trial counting, failed-attempt logging, artifact retention, and acceptance blockers.
- Next action: Use the Stage 9 package as the mandatory pre-task check before any Stage 10 work is opened.

## ADR-011 - Stage 10 robustness testing baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 10 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 10 charter, checklist, scope, and robustness map as the current operating baseline for robustness-testing governance.
- Rationale: These artifacts define the governed robustness checks, parameter sensitivity rules, stress-testing expectations, regime-shift analysis, sample perturbation rules, and the blockers that prevent fragile results from moving forward.
- Next action: Use the Stage 10 package as the mandatory pre-task check before any Stage 11 work is opened.

## ADR-012 - Stage 11 walk-forward validation baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 11 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 11 charter, checklist, scope, and validation map as the current operating baseline for walk-forward validation governance.
- Rationale: These artifacts define the governed walk-forward windows, embargo/purge controls, train/validation/test splits, regime-aware acceptance thresholds, required validation artifacts, and promotion blockers.
- Next action: Use the Stage 11 package as the mandatory pre-task check before any Stage 12 work is opened.
