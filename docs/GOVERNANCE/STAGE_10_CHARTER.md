# QROS - Stage 10 Robustness Testing Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1-10, Stage 1-9 packages, Project State reference-only note.

> **Ratification note.** The Constitution remains draft governance. Stage 10 makes no claim of ratification, production readiness, or approval. Reference-only folders (`.claude/`, `_extracted/`, `scratch/`, `trading_engine/`) are read-only context, not governance baseline.

## 1. Purpose
Define how QROS **performs robustness testing on governed research results** so that results are not accepted on the basis of a single fragile sample, parameter setting, or market regime. Stage 10 fixes parameter stability requirements, sensitivity analysis expectations, stress testing requirements, regime-shift and subperiod analysis, sample perturbation expectations, the definition of robustness evidence, and what blocks a result from moving forward. It builds no robustness, statistics, research, feature, hypothesis, strategy, backtest, or execution code.

## 2. Governing authority
- Constitution - Articles IV, V, VI, VIII, IX (evidence before opinion; data precedes conclusions; scientific lifecycle; engineering standards; governance/traceability).
- Founding Governance - Bill of Rights Article 1 (Reproducibility), Article 3 (Honest Evaluation), Article 4 (Failure); Code of Scientific Conduct Principles 2, 5, 6 (falsifiability; negative results valued; avoid confirmation bias).
- Master Handbook - Part 10 (Edge Discovery) as primary; Parts 2, 7, 8 (bias eliminations — sampling bias/stress-period coverage; pipeline robustness gate; bootstrap/permutation).
- Stage 1-9 governance packages; Project State reference-only note; ADR-001.

## 3. What robustness means in QROS
A result is **robust** when it survives perturbation to its parameters, data samples, and market regimes, and is **not a false edge** — not a product of curve-fitting, data mining, coincidence/luck, execution mirage, or capacity limitation (Part 10 §2). Robustness is verified through non-parametric resampling, multi-decade sample coverage, parameter-shift stability, and the five false-edge diagnostics. No result is accepted on the basis of a single fragile sample or parameter setting.

## 4. Allowed work (Stage 10)
- Author the robustness-rule map (parameter stability, sensitivity analysis, stress testing, regime-shift/subperiod analysis, sample perturbation, robustness-evidence definition, promotion blockers).
- Specify the mandatory stress and sensitivity checks and the failure/blocking protocol.
- Produce governance/specification documents only.

## 5. Prohibited work (Stage 10)
- **No** robustness, statistics, research, feature, hypothesis, strategy, backtest, or execution code.
- **No** live trading, order dispatch, or execution code.
- **No** strategy development outside the governed workflow.
- **No** uncontrolled backtesting or stress testing.
- **No** claim of ratification, production readiness, or approval.

## 6. Entry criteria
- Stages 1-9 packages committed and accepted; Project State reference-only note in effect.
- Constitution treated as draft.
- Scope limited to robustness-testing **specification** (Parts 1-10).

## 7. Exit criteria
- Robustness map, charter, checklist, and scope documented, consistent, and approved.
- Every robustness rule and threshold traceable to a governing source.
- No prohibited work performed; no implementation artifacts.
- Artifacts for Stage 11 entry specified (see `STAGE_10_SCOPE.md` §Outputs).

## 8. Do-not-proceed (blocking)
Before the Stage 10 robustness rules are approved, the following are forbidden and halt work:
1. **No** strategy implementation, uncontrolled backtesting, execution of any kind, or approval claims.
2. **No** result accepted on the basis of a single fragile sample, parameter setting, or market regime.
3. **No** claim of ratification, production readiness, or approval.

See `STAGE_10_CHECKLIST.md` gate **G0** for the operational blocking gate.
