# QROS - Stage 6 Hypothesis-Generation Rule Map

Specification-only. Grounded in Master Handbook Part 6 (plus Parts 1-5, Stage 3/4/5 packages, and ADR-003). Thresholds/mechanics taken verbatim and must not be relaxed.

**MAND** = mandatory; **BLOCK** = what a failure halts.

---

## 1. Valid hypothesis sources
- **Rule G6-01:** Candidates must be grounded in **structural mechanics, not pattern matching** (Part 6 §1 mandate). Valid sources:
  1. The documented anomaly mechanics below (G6-03).
  2. Literature / market observation explicitly tied to one of those mechanics.
  3. Approved data and approved feature dependencies (Stages 3/4) that express the mechanic.
- **MAND:** Every candidate names the mechanic it derives from and the approved data/feature it depends on.
- **Source:** Part 6 §1; Stages 3-4.
- **BLOCK:** Any candidate without a documented source/mechanic is invalid.

## 2. Economic rationale requirements
- **Rule G6-02:** Every candidate carries an economic and/or behavioral rationale: the root cause of the mechanic, when it decays, how it is measured, and its falsification test (Part 6 §1 columns).
- **MAND:** The rationale maps to the candidate's Stage 5 record fields (HYP-03 Market Logic, HYP-04 Economic Theory, HYP-05 Behavioral Theory, HYP-06 Expected Edge, HYP-13/14/15 literature).
- **Source:** Part 6 §1; Part 5.
- **BLOCK:** Rationale-free or purely statistical candidates are invalid.

## 3. Anomaly / behavioral mechanic categories
- **Rule G6-03:** Candidates may draw on the **6 documented mechanics** only (Part 6 §1; ADR-003). The claimed "15" is a heading; only these 6 are documented, and **no mechanic is invented**:
  1. Microstructure Liquidity Imbalance
  2. Dealer Gamma Pinning (GEX)
  3. ETF Creation/Redemption Flow
  4. End-of-Month Index Rebalancing
  5. Volatility Risk Premium (VRP)
  6. Cross-Asset Interest Rate Spillover
- **MAND:** Categories MECH-07..MECH-15 are **empty registration slots** and require a documented amendment (ADR-003; Constitution Art. XI) before any candidate may use them.
- **Source:** Part 6 §1; ADR-003.
- **BLOCK:** Any candidate using an undocumented/empty mechanic slot is invalid.

## 4. Regime-awareness expectations
- **Rule G6-04:** Every candidate must be **regime-aware**: it states the market conditions where the edge is expected to manifest (Part 6 §2; HYP-07).
- **MAND:** Regime detection (HMM / MS-VAR, Part 6 §2) is a **reference** for candidate framing, not an implementation here. An edge that **vanishes under high volatility or elevated funding rates is an implicit short-volatility exposure, not true alpha** (Part 6 §2) — such candidates must be flagged, not advanced.
- **Source:** Part 6 §2; Part 5 HYP-07.
- **BLOCK:** A regime-blind or short-vol-masking candidate is blocked.

## 5. What makes a hypothesis candidate valid
- **Rule G6-05:** A candidate is **valid** when **all** hold:
  1. Falsifiable (Code of Conduct Principle 2) and mechanic-grounded (G6-01, G6-03).
  2. Carries economic/behavioral rationale (G6-02).
  3. Regime-aware, no short-vol masking (G6-04).
  4. Data and features traceable to approved Stages 3/4; ready for Stage 5 registration/lock.
  5. No edge or strategy claim.
- **Source:** Part 6; Stages 3-5; Code of Conduct Principle 2.
- **BLOCK:** Any unmet condition makes the candidate invalid.

## 6. What blocks a candidate from moving forward
- **Rule G6-06:** A candidate is **blocked** if: it is unfalsifiable; it lacks a documented mechanic or uses an empty slot (MECH-07..15 without amendment); it is rationale-free or pattern-matching only; its data/features are not from approved Stages 3/4; it masks short-vol exposure; it asserts an edge/strategy; or it is advanced to testing without Stage 5 registration, lock, and pre-testing approval.
- **MAND:** Blocking reasons are recorded in the decision log; no candidate is silently dropped or forcibly advanced.
- **Source:** Part 6; Part 5 §2; ADR-003; ADR-001.
- **BLOCK:** Any blocker halts that candidate's progress.

## 7. How hypotheses differ from tested strategies
- **Rule G6-07:** A **hypothesis** is a falsifiable, pre-registered statement to be tested (Part 5). A **tested strategy** is a validated model that has passed the full research pipeline and approval (Part 7, Stages 11-15). Stage 6 produces only **candidates/hypotheses** — never tested strategies.
- **MAND:** No candidate may carry performance metrics, backtest results, or production claims. Those belong to later stages after validation.
- **Source:** Part 5; Part 7; Constitution Art. VI.
- **BLOCK:** Any candidate presented as a tested strategy or edge is invalid and halted.

---

## Allowed generation sources (summary)
The 6 documented anomaly mechanics; literature/observation tied to them; approved Stage 3/4 data and features expressing a mechanic; regime-aware framing.

## Forbidden generation sources (summary)
Pattern matching without a mechanic · invented mechanics (MECH-07..15 without amendment) · rationale-free/statistical-only candidates · short-vol-masking candidates · any candidate asserting edge/strategy/performance.

## Artifacts that must exist before Stage 7 begins
1. A documented set of **valid candidate hypotheses** (each grounding a mechanic, rationale, regime, and Stage 3/4 dependencies).
2. Each candidate's Stage 5 registration status (pending → locked → pre-testing approved).
3. A decision-log entry recording the candidate set and any blocked candidates.
4. Confirmation that no candidate carries a tested-strategy or edge claim.
