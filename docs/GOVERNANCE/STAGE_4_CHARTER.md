# QROS - Stage 4 Feature Engineering Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1-4, Stage 1-3 packages, Project State reference-only note.

> **Ratification note.** The Constitution remains draft governance. Stage 4 makes no claim of ratification, production readiness, or approval. Reference-only folders (`.claude/`, `_extracted/`, `scratch/`, `trading_engine/`) are read-only context; they are not governance baseline and must not be deleted without supervisor authorization.

## 1. Purpose
Define how QROS turns **approved, quality-checked data** into feature **specifications** without leaking future information or drifting into hypothesis or strategy work. Stage 4 fixes which transformations are allowed, which are forbidden, and the approval rules every feature set must satisfy. It builds no feature, model, research, backtest, or execution code.

## 2. Governing authority
- Constitution - Articles IV, V, VI, IX (evidence; data precedes conclusions; traceability).
- Founding Governance - Bill of Rights (Reproducibility, Traceability, Documentation); Code of Scientific Conduct Principle 3.
- Master Handbook - Part 4 (Feature Engineering) as primary; Parts 1-3 (data foundation, data quality).
- Stage 1 Governance Lock; Stage 2 Data Foundation; Stage 3 Data Quality packages.

## 3. What counts as an approved feature in QROS
A feature is **approved** only when all hold:
1. It derives from an **approved, quality-checked frozen snapshot** (Stage 3 M3-01..M3-08).
2. It is defined **mathematically** in the approved taxonomy (`STAGE_4_FEATURE_MAP.md`), with formula, parameters, and window.
3. It passes **ADF stationarity** (p < 0.05) and **multicollinearity** (VIF < 10.0; correlation < 0.85) checks.
4. It is computed using **backward-looking rolling/expanding windows only** (no look-ahead).
5. It is **recorded with provenance** (source snapshot, definition, parameters, version).
6. It carries **no** hypothesis or edge claim.

## 4. Allowed work (Stage 4)
- Author the feature-rule map (categories, stationarity/normalization, leakage prevention, rolling-window conventions, target/label separation, provenance, approval thresholds).
- Specify allowed vs forbidden transformations.
- Specify the artifacts required before Stage 5.
- Produce governance/specification documents only.

## 5. Prohibited work (Stage 4)
- **No** feature, model, research, backtest, or execution code.
- **No** model training; **no** backtesting or live trading.
- **No** hypothesis registration or edge claims.
- **No** global/full-sample fitting of any normalization parameter.
- **No** dataset used for features unless it passed Stage 3 quality approval.

## 6. Entry criteria
- Stages 1-3 packages committed and accepted; Project State marks `.claude/`, `_extracted/`, `scratch/`, `trading_engine/` reference-only.
- Constitution treated as draft.
- Scope limited to feature **specification** (Parts 1-4).

## 7. Exit criteria
- Feature map, charter, checklist, and scope are documented, consistent, and approved.
- Every rule and threshold traceable to a governing source; every approved feature traceable to the approved data foundation and Stage 3 quality rules.
- No prohibited work performed; no implementation artifacts.
- Artifacts for Stage 5 entry specified (see `STAGE_4_SCOPE.md` §Outputs).

## 8. Do-not-proceed (blocking)
Before the Stage 4 feature rules are approved, the following are forbidden and halt work:
1. **No** hypothesis generation, edge discovery, backtesting, or execution of any kind.
2. **No** feature set approved unless traceable to the approved data foundation and Stage 3 quality rules.
3. **No** relaxation of any feature threshold to force a pass.
4. **No** ratification / approval / production-readiness claim.

See `STAGE_4_CHECKLIST.md` gate **G0** for the operational blocking gate.
