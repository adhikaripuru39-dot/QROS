# QROS - Stage 3 Data Quality Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1-3, Stage 1 Governance Lock, Stage 2 Data Foundation.

> **Ratification note.** The Constitution remains draft governance. Stage 3 makes no claim of ratification, production readiness, or approval. It inherits the Stage 1 rule that such claims require the constitution itself to be updated first.

## 1. Purpose
Define how QROS validates **trust in data** before any later stage may use it. Stage 3 is specification-only: it fixes the mandatory quality checks, their thresholds, and the failure rules that block downstream feature, hypothesis, edge, backtest, and execution work. It may not build any pipeline, feature, hypothesis, strategy, backtest, or execution code.

## 2. Governing authority
- Constitution - Articles IV, V, VI, VII, IX (evidence before opinion; data precedes conclusions; traceability).
- Founding Governance - Bill of Rights (Reproducibility, Traceability, Documentation), Code of Scientific Conduct **Principle 3** (every dataset must be validated: completeness, missing values, timestamps, duplicates, quality, provenance).
- Master Handbook - Part 1 (Data Collection / validation SOPs), Part 2 (Data Quality Management / bias elimination), Part 3 (Data Engineering / snapshot registry & lineage).
- Stage 1 Governance Lock and Stage 2 Data Foundation packages.

## 3. What data quality means in QROS
A dataset is **trustworthy** only when it is: complete, timestamp-integrous, deduplicated, free of uncorrected bad ticks, missing-data handled **without look-ahead**, point-in-time correct, provenance/correction recorded, and passing the mandated approval thresholds (Part 2 firewall; Code of Conduct Principle 3). Untrusted data is unusable by any downstream stage.

## 4. Allowed work (Stage 3)
- Author the quality-rule map (completeness, timestamp integrity, duplicates, bad-tick, missing-data, point-in-time/no-lookahead, provenance & correction, approval thresholds).
- Specify mandatory checks, their thresholds, and the failures that block downstream work.
- Specify the artifacts that must exist before Stage 4 may begin.
- Produce governance/specification documents only.

## 5. Prohibited work (Stage 3)
- **No** pipeline, feature, hypothesis, strategy, backtest, or execution code.
- No feature engineering implementation; no hypothesis generation or edge discovery.
- No backtesting, walk-forward validation, or live execution.
- No claim of ratification, approval, or production readiness.
- No dataset freeze for experimentation until Stage 3 quality rules and approvals exist.

## 6. Entry criteria
- Stage 1 Governance Lock and Stage 2 Data Foundation are committed and accepted.
- Constitution remains treated as draft governance.
- Scope is explicitly limited to data-quality specification (Parts 1-3).

## 7. Exit criteria
- Quality-rule map, charter, checklist, and scope are documented, consistent, and approved.
- Every mandatory check, threshold, and downstream blocker is traceable to a governing source.
- No prohibited work was performed.
- The required artifacts for Stage 4 entry are specified (see `STAGE_3_SCOPE.md` §Outputs).

## 8. Do-not-proceed (blocking)
Before the Stage 3 quality rules are approved, the following are forbidden and halt work:
1. **No** feature, hypothesis, edge, backtest, or execution work of any kind.
2. **No** promotion of any dataset to production/feature store, and **no** freeze for experimentation.
3. **No** relaxation of any quality threshold to force a dataset to pass.
4. **No** ratification / approval / production-readiness claim.

See `STAGE_3_CHECKLIST.md` gate **G0** for the operational blocking gate.
