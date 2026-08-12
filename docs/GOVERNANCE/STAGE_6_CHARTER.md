# QROS - Stage 6 Hypothesis Generation Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1-6, Stage 1-5 packages, Project State reference-only note.

> **Ratification note.** The Constitution remains draft governance. Stage 6 makes no claim of ratification, production readiness, or approval. Reference-only folders (`.claude/`, `_extracted/`, `scratch/`, `trading_engine/`) are read-only context, not governance baseline.

## 1. Purpose
Define how QROS **generates candidate hypotheses from approved data and approved features** without turning them into tested strategies. Stage 6 fixes which sources are allowed, which are forbidden, and what makes a candidate valid or blocked. It builds no hypothesis, feature, strategy, backtest, or execution code.

## 2. Governing authority
- Constitution - Articles IV, V, VI (evidence; data precedes conclusions; falsify-then-validate).
- Founding Governance - Code of Scientific Conduct **Principle 2** (falsifiability), Principle 6 (avoid confirmation bias).
- Master Handbook - Part 6 (Hypothesis Generation) as primary; Parts 1-5 (data, quality, features, hypothesis management).
- Stage 1-5 governance packages; Project State reference-only note; ADR-003.

## 3. What counts as a hypothesis candidate in QROS
A **candidate** is a falsifiable, economically and behaviorally motivated research idea that:
1. Is grounded in a **documented anomaly mechanic** (Part 6) and approved data/feature foundations (Stages 3/4).
2. Is **regime-aware** (notes the market conditions where it is expected to manifest).
3. Is a **pre-registration proposal** — it has not been tested and is not a strategy or an edge claim.
4. Is intended to be registered, locked, and approved under Stage 5 rules before any testing.

A candidate is **not** a tested strategy; it carries **no** performance, edge, or approval claim.

## 4. Allowed work (Stage 6)
- Author the generation-rule map (sources, rationale, mechanic categories, regime-awareness, validity, blockers, hypothesis-vs-strategy).
- Specify allowed vs forbidden generation sources.
- Reference approved feature/data dependencies (no feature engineering).
- Produce governance/specification documents only.

## 5. Prohibited work (Stage 6)
- **No** hypothesis, feature, strategy, backtest, or execution code.
- **No** hypothesis testing, training, backtesting, or live execution.
- **No** edge claims and **no** strategy claims.
- **No** feature engineering beyond referencing approved feature dependencies.
- **No** invented anomaly mechanic outside the documented set without an amendment (ADR-003).

## 6. Entry criteria
- Stages 1-5 packages committed and accepted; Project State reference-only note in effect.
- Constitution treated as draft.
- Scope limited to hypothesis **generation specification** (Parts 1-6).

## 7. Exit criteria
- Generation map, charter, checklist, and scope documented, consistent, and approved.
- Every rule traceable to a governing source; allowed/forbidden sources specified.
- No prohibited work performed; no implementation artifacts.
- Artifacts for Stage 7 entry specified (see `STAGE_6_SCOPE.md` §Outputs).

## 8. Do-not-proceed (blocking)
Before the Stage 6 generation rules are approved, the following are forbidden and halt work:
1. **No** edge discovery, testing, backtesting, or execution of any kind.
2. **No** candidate advanced to testing unless it is registered, locked, and pre-testing approved under Stage 5.
3. **No** edge or strategy claim attached to any candidate.
4. **No** ratification / approval / production-readiness claim.

See `STAGE_6_CHECKLIST.md` gate **G0** for the operational blocking gate.
