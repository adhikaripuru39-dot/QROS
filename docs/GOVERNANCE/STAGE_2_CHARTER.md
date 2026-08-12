# QROS - Stage 2 Data Foundation Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1-3.

> **Ratification note.** The Constitution remains draft governance. Stage 2 inherits the Stage 1 rule that no claim of ratification, production readiness, or approval may be made unless the constitution itself is formally updated.

## 1. Purpose
Establish the data-foundation boundary for QROS so later work can be built on a documented, reproducible, and approved data base. Stage 2 may define and verify data structures, source boundaries, lineage rules, and quality requirements. It may not create trading logic, hypotheses, or execution behavior.

## 2. Governing authority
- Constitution - Articles IV, V, VI, VII, VIII, IX
- Founding Governance - Bill of Rights, Bill of Responsibilities, Code of Scientific Conduct
- Master Handbook - Parts 1, 2, and 3
- Stage 1 Governance Lock artifacts

## 3. Allowed work (Stage 2)
- Define the approved data domains, source boundaries, and provenance rules.
- Specify input/output contracts for data collection, quality, and engineering.
- Define canonical schemas, identifiers, timestamps, and lineage requirements.
- Specify validation rules for completeness, consistency, freshness, and traceability.
- Produce governance/specification artifacts for data-only work.

## 4. Prohibited work (Stage 2)
- No engine, module, or strategy implementation.
- No feature engineering logic beyond data-contract specification.
- No hypothesis creation, registration, or testing.
- No backtests, walk-forward runs, or live execution.
- No claim that any edge, model, or strategy is approved.
- No dataset freeze for experimentation unless the data scope and quality rules are approved first.

## 5. Entry criteria
- Stage 1 Governance Lock is committed and accepted.
- Constitution remains treated as draft governance.
- Scope for data foundation work is explicitly limited to Parts 1-3.

## 6. Exit criteria
- Data scope, inputs, outputs, and validation rules are documented and approved.
- Canonical data contracts exist for the Stage 2 boundary.
- No prohibited work was performed.
- The decision log records Stage 2 approval and any open follow-ups.

## 7. Relationship to later stages
Stage 2 is the foundation for Stage 3 data quality and Stage 4 data engineering planning. It does not authorize implementation in those areas; it only prepares the approved specification surface.
