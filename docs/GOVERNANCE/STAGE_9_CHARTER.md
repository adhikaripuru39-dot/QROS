# QROS - Stage 9 Experiment Tracking Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1-9, Stage 1-8 packages, Project State reference-only note.

> **Ratification note.** The Constitution remains draft governance. Stage 9 makes no claim of ratification, production readiness, or approval. Reference-only folders (`.claude/`, `_extracted/`, `scratch/`, `trading_engine/`) are read-only context, not governance baseline.

## 1. Purpose
Define how QROS **records, traces, and preserves experiment history** so every trial is reproducible, auditable, and linked to its data, code, and approval context. Stage 9 fixes the required experiment-record fields, git-commit and dataset-snapshot linkage, seed/parameter/environment capture, trial counting and failed-attempt logging, artifact retention, and decision-log/registry cross-linking. It builds no tracking, statistics, research, feature, hypothesis, strategy, backtest, or execution code.

## 2. Governing authority
- Constitution - Articles V, VI, IX (data precedes conclusions; scientific lifecycle; governance/versioning/archival).
- Founding Governance - Bill of Rights Article 1 (Reproducibility), Article 4 (Failure); Code of Scientific Conduct Principles 4 and 6 (experiment documentation, avoid confirmation bias).
- Master Handbook - Part 9 (Experiment Tracking) as primary; Parts 2, 7, 8 (DSR trial-count linkage; pipeline Experiment Registry; statistical test outputs).
- Stage 1-8 governance packages; Project State reference-only note; ADR-001.

## 3. What experiment tracking is in QROS
The **mandatory, immutable record** of every experiment and trial — the 17-field EXP record (EXP-01..EXP-17, Part 9 §1), linked to its dataset SHA-256 snapshot, git commit, feature version, hypothesis, and approval context, with total trial count **N** fed directly into the Deflated Sharpe Ratio (Part 9 §2). The record is **append-only**: no hidden trials, no unlogged experimentation, no retroactive editing.

## 4. Allowed work (Stage 9)
- Author the tracking-rule map (record fields, snapshot/git linkage, seed/parameter/environment capture, trial counting & failed-attempt logging, artifact retention, cross-linking, acceptance blockers).
- Specify what makes an experiment record complete.
- Produce governance/specification documents only.

## 5. Prohibited work (Stage 9)
- **No** tracking, statistics, research, feature, hypothesis, strategy, backtest, or execution code.
- **No** live trading, order dispatch, or execution code.
- **No** strategy development outside the governed workflow.
- **No** hidden or unlogged experimentation; **no** retroactive editing or back-dating of records.
- **No** claim of ratification, production readiness, or approval.

## 6. Entry criteria
- Stages 1-8 packages committed and accepted; Project State reference-only note in effect.
- Constitution treated as draft.
- Scope limited to experiment-tracking **specification** (Parts 1-9).

## 7. Exit criteria
- Tracking map, charter, checklist, and scope documented, consistent, and approved.
- Every record field and linkage traceable to a governing source.
- No prohibited work performed; no implementation artifacts.
- Artifacts for Stage 10 entry specified (see `STAGE_9_SCOPE.md` §Outputs).

## 8. Do-not-proceed (blocking)
Before the Stage 9 tracking rules are approved, the following are forbidden and halt work:
1. **No** untracked experimentation, hidden trials, or unlogged failed attempts.
2. **No** retroactive editing, back-dating, or deletion of experiment records.
3. **No** strategy implementation, uncontrolled backtesting, execution, or approval claims.
4. **No** ratification / approval / production-readiness claim.

See `STAGE_9_CHECKLIST.md` gate **G0** for the operational blocking gate.
