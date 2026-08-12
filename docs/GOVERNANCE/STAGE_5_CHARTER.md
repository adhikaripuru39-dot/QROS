# QROS - Stage 5 Hypothesis Management Charter

**Status:** Governance-only · **Scope:** One page · **Authority:** QROS Constitution (Draft for Ratification), Founding Governance Documents, Master Handbook Parts 1-5, Stage 1-4 packages, Project State reference-only note.

> **Ratification note.** The Constitution remains draft governance. Stage 5 makes no claim of ratification, production readiness, or approval. It inherits the Stage 1 rule that such claims require the constitution itself to be updated first.

## 1. Purpose
Define how QROS **registers, locks, and governs hypotheses before any research or testing begins.** Stage 5 is specification-only: it fixes hypothesis identity, the full record, rationale and falsifiability, pre-registration and SHA-256 locking, ownership/approval, and the eligibility/blocking rules. It builds no hypothesis, feature, strategy, backtest, or execution code.

## 2. Governing authority
- Constitution - Articles IV, V, VI (evidence; data precedes conclusions; scientific method / falsify-then-validate).
- Founding Governance - Bill of Rights (Traceability, Honest Evaluation); Code of Scientific Conduct **Principle 2** (falsifiability) and Principle 6 (avoid confirmation bias).
- Master Handbook - Part 5 (Hypothesis Management) as primary; Parts 1-4 (data foundation, quality, features).
- Stage 1-4 governance packages; Project State reference-only note.

## 3. What counts as a valid QROS hypothesis
A hypothesis is **valid** only when it is:
1. A **falsifiable**, economically and behaviorally motivated research question (Code of Conduct Principle 2; Part 5).
2. Registered with **all 22 fields** present (HYP-01..HYP-22; Part 5 §1).
3. **SHA-256 locked** at submission and never modified post-lock (Part 5 §2).
4. **Pre-testing approved** by Head of Research and Lead Statistician before any code execution (Part 5 §2).

A hypothesis that has not been registered, locked, and approved is **not** eligible for any research or testing.

## 4. Allowed work (Stage 5)
- Author the hypothesis-rule map (identity, full record, rationale/falsifiability, pre-registration & lock, ownership/approval, eligibility, blockers).
- Specify the 22-field record and how the lock works.
- Document hypothesis inputs and dependencies (data quality, features) — **documentation only, no feature work**.
- Produce governance/specification documents only.

## 5. Prohibited work (Stage 5)
- **No** hypothesis, feature, strategy, backtest, or execution code.
- **No** hypothesis testing, training, backtesting, or live execution.
- **No** strategy logic and **no** edge claims.
- **No** feature work beyond documenting hypothesis inputs and dependencies.
- **No** modification of a locked hypothesis to fit results.

## 6. Entry criteria
- Stages 1-4 packages committed and accepted; Project State reference-only note in effect.
- Constitution treated as draft.
- Scope limited to hypothesis **specification** (Parts 1-5).

## 7. Exit criteria
- Hypothesis map, charter, checklist, and scope documented, consistent, and approved.
- Every rule traceable to a governing source; the 22-field record and lock mechanism specified.
- No prohibited work performed; no implementation artifacts.
- Artifacts for Stage 6 entry specified (see `STAGE_5_SCOPE.md` §Outputs).

## 8. Do-not-proceed (blocking)
Before the Stage 5 hypothesis rules are approved, the following are forbidden and halt work:
1. **No** feature expansion, edge discovery, backtesting, or execution of any kind.
2. **No** hypothesis tested, trained, or otherwise advanced without registration, lock, and pre-testing approval.
3. **No** relaxation of eligibility or approval criteria to force a hypothesis forward.
4. **No** ratification / approval / production-readiness claim.

See `STAGE_5_CHECKLIST.md` gate **G0** for the operational blocking gate.
