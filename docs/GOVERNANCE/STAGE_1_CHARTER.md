# QROS — Stage 1 Governance Lock: Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1–10.

> **Ratification note.** The Constitution file itself still carries `Status: Draft for Ratification`. `DECISION_LOG.md` ADR-006 claims ratification, but the governing document has not been updated to reflect it. Stage 1 therefore governs under **draft** status and makes **no** claim of ratification, production readiness, or approval. Discrepancy flagged for resolution before any later stage relies on a ratified baseline.

## 1. Purpose
Lock the governance basis for all downstream QROS work. Stage 1 produces **no** research, model, backtest, or execution artifact. It only fixes **scope, inputs, outputs, and edge-confirmation requirements**, which gate every later stage.

## 2. Governing authority (binding on this stage)
- Constitution — Articles IV, V, VI, VII, IX (values; research precedes implementation; scientific method; risk before profit; traceability).
- Founding Governance — Bill of Rights (Reproducibility, Traceability, Honest Evaluation, Documentation, Risk Protection), Bill of Responsibilities, Code of Scientific Conduct **Principle 8** (production requires independent validation).
- Master Handbook Parts 1–10 and the 15-stage pipeline (Part 7).

## 3. Allowed work (Stage 1)
- Read, map, and reconcile the governing documents.
- Document **scope, inputs, outputs, and edge-confirmation** criteria in writing.
- Produce governance artifacts (this charter, stage map, compliance checklist, decision/amendment records).
- Author threshold and gate values as **proposed policy text** (to live in `governance/policy.py` later — never hard-coded in an engine in Stage 1).
- Draft data / variable / schema **specifications** (not implementations).

## 4. Prohibited work (Stage 1)
- **No engine or module implementation** of any kind.
- **No** research, strategy, backtest, or live-execution code.
- **No** live trading, order dispatch, position sizing, or risk-limit execution.
- **No** retroactive relaxation of any threshold or quality gate.
- **No** claim of ratification, production readiness, or approval.
- **No** HYP registered as tested; **no** dataset snapshot frozen for experimentation.
- **No** experiment/trial execution logged against an accepted hypothesis.

## 5. Entry criteria (to start Stage 1)
- Governing documents exist and are read end-to-end (Constitution, Founding Governance, Handbook Parts 1–10).
- A named owner accepts the draft-constitution status and the no-approval constraint.
- Any pre-existing codebase is treated as **not** compliance-assumed and is out of scope for Stage 1.

## 6. Exit criteria (to close Stage 1)
- Charter, stage map, compliance checklist, and do-not-proceed list all exist and are internally consistent.
- Every allowed and prohibited item is traceable to a governing source (section/part cited).
- **Scope, inputs, outputs, and edge confirmation are documented and approved** by the owner.
- No prohibited work was performed; zero implementation artifacts produced.
- Resolution of the ratification discrepancy is recorded in the decision log.

## 7. Definition of "edge confirmation" (used throughout)
From Part 10: an edge is a *statistically persistent, economically justified positive expected return after costs*. It is **confirmed** only by pre-registered acceptance criteria, e.g. DSR p < 0.01 (Part 8), OOS Sharpe > 2.0 / MaxDD < 15% (Part 7 Stage 11), t-stat > 3.0 (Stage 9), and survival of the 5 false-edge diagnostics (Part 10). Edge confirmation must be documented **before** any Stage 2 engine work; it is never inferred from a backtest.

## 8. Relationship to the 15-stage pipeline
This charter is **Stage 0 — the governance lock**. It must pass before Pipeline Stage 1 (Idea Generation) may be attempted. See `STAGE_SEQUENCE_MAP.md` for the ordering.
