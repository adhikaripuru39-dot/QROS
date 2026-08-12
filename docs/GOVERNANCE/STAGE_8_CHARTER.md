# QROS - Stage 8 Statistical Research Methodology Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1-8, Stage 1-7 packages, Project State reference-only note.

> **Ratification note.** The Constitution remains draft governance. Stage 8 makes no claim of ratification, production readiness, or approval. Reference-only folders (`.claude/`, `_extracted/`, `scratch/`, `trading_engine/`) are read-only context, not governance baseline.

## 1. Purpose
Define the **statistical methodology rules** that govern how QROS tests hypotheses and research results — without p-hacking, threshold drift, or retroactive approval. Stage 8 fixes the required statistical tests and where they apply, multiple-testing control, false-discovery and family-wise error rules, out-of-sample and cross-validation expectations, minimum evidence thresholds, and robustness/sensitivity requirements. It builds no statistics, research, feature, hypothesis, strategy, backtest, or execution code.

## 2. Governing authority
- Constitution - Articles IV, V, VI, VIII, IX (evidence before opinion; data precedes conclusions; scientific lifecycle; engineering standards; governance/traceability).
- Founding Governance - Bill of Rights (Honest Evaluation, Reproducibility, Failure); Code of Scientific Conduct (Principles 2, 6, 8: falsifiability, avoid confirmation bias, independent validation).
- Master Handbook - Part 8 (Statistical Research Methodology) as primary; Parts 2 and 7 (data-quality bias eliminations and DSR/FWER; pipeline stage gates). Part 9 is referenced only as a downstream experiment-record dependency, not as an authority to expand Stage 8 scope.
- Stage 1-7 governance packages; Project State reference-only note; ADR-001.

## 3. What statistical methodology is in QROS
The **mandatory set of inference and correction rules** — frequentist inference, multiple-testing corrections (DSR, FDR-BH, FWER-Holm), CPCV out-of-sample validation, and non-parametric robustness (stationary bootstrap, permutation tests) — that governs how any hypothesis or research result is tested and judged. Bayesian inference is not mandated by this package; if ever introduced, it must be added by a separate governed amendment. This methodology applies **before any result moves toward validation**; it permits **no p-hacking, no threshold drift, and no retroactive approval**.

## 4. Allowed work (Stage 8)
- Author the statistics-rule map (required tests and application domains, multiple-testing control, FDR/FWER rules, OOS/CV expectations, minimum evidence thresholds, robustness/sensitivity, promotion blockers).
- Specify the mandatory statistical evidence and the failure/blocking protocol.
- Produce governance/specification documents only.

## 5. Prohibited work (Stage 8)
- **No** statistics, research, feature, hypothesis, strategy, backtest, or execution code.
- **No** live trading, order dispatch, or execution code.
- **No** strategy development outside the governed methodology.
- **No** uncontrolled backtesting or p-hacking.
- **No** claim of ratification, production readiness, or approval.

## 6. Entry criteria
- Stages 1-7 packages committed and accepted; Project State reference-only note in effect.
- Constitution treated as draft.
- Scope limited to statistical-methodology **specification** (Parts 1-8).

## 7. Exit criteria
- Statistics map, charter, checklist, and scope documented, consistent, and approved.
- Every test, correction, and threshold traceable to a governing source.
- No prohibited work performed; no implementation artifacts.
- Artifacts for Stage 9 entry specified (see `STAGE_8_SCOPE.md` §Outputs).

## 8. Do-not-proceed (blocking)
Before the Stage 8 statistics rules are approved, the following are forbidden and halt work:
1. **No** strategy implementation, uncontrolled backtesting, execution of any kind, or approval claims.
2. **No** result promoted toward validation without its required statistical evidence and multiple-testing correction.
3. **No** p-hacking, threshold drift, or retroactive approval.
4. **No** ratification / approval / production-readiness claim.

See `STAGE_8_CHECKLIST.md` gate **G0** for the operational blocking gate.
