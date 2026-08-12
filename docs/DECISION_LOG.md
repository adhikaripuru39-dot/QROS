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
