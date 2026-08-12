# QROS - Stage 5 Hypothesis-Rule Map

Specification-only. Grounded in Master Handbook Part 5 (plus Parts 1-4, Stage 3/4 packages, and the Code of Scientific Conduct). Thresholds and fields are taken verbatim and must not be relaxed (ADR-001).

**MAND** = mandatory; **BLOCK** = what a failure halts.

---

## 1. Hypothesis identity & naming
- **Rule H5-01:** Every hypothesis has a **globally unique Hypothesis ID** (HYP-01) using the institutional pattern `HYP-<ASSET>-<MECHANISM>-<YEAR>-<SEQ>` (e.g. `HYP-EQUITY-MICROSTRUCTURE-2026-0042`) (Part 5 §1 HYP-01).
- **MAND:** The ID is unique and stable; it is the key for the research registry and all experiment records.
- **Source:** Part 5 §1 HYP-01.
- **BLOCK:** Missing or duplicated ID blocks registration and all downstream tracking.

## 2. Full hypothesis record fields
- **Rule H5-02:** A hypothesis is not registerable until **all 22 fields (HYP-01..HYP-22)** are complete (Part 5 §1).
  | ID | Field | ID | Field |
  | :- | :--- | :- | :--- |
  | HYP-01 | Hypothesis ID | HYP-12 | Expected Direction |
  | HYP-02 | Research Question | HYP-13 | Supporting Literature |
  | HYP-03 | Market Logic | HYP-14 | Contradicting Literature |
  | HYP-04 | Economic Theory | HYP-15 | Alternative Explanations |
  | HYP-05 | Behavioral Theory | HYP-16 | Data Requirements |
  | HYP-06 | Expected Edge | HYP-17 | Testing Requirements |
  | HYP-07 | Market Conditions | HYP-18 | Acceptance Criteria |
  | HYP-08 | Assumptions | HYP-19 | Rejection Criteria |
  | HYP-09 | Independent Variables | HYP-20 | Confidence Level |
  | HYP-10 | Dependent Variables | HYP-21 | Replication Requirements |
  | HYP-11 | Control Variables | HYP-22 | Retirement Criteria |
- **MAND:** All 22 present and non-empty before registration; HYP-09/10/11 reference approved Stage 4 features and Stage 3 quality data.
- **Source:** Part 5 §1.
- **BLOCK:** Any missing field blocks registration and all testing eligibility.

## 3. Economic rationale & falsifiability
- **Rule H5-03:** The hypothesis must carry economic and behavioral rationale (HYP-03 Market Logic, HYP-04 Economic Theory, HYP-05 Behavioral Theory), supporting and contradicting literature (HYP-13/14), and alternative explanations (HYP-15) (Part 5 §1).
- **MAND:** The Research Question (HYP-02) and Expected Direction (HYP-12) are stated so the hypothesis is **falsifiable** — testable in a way that could prove it wrong (Code of Conduct Principle 2; Constitution Art. VI).
- **Source:** Part 5 §1; Code of Conduct Principle 2.
- **BLOCK:** Unfalsifiable or rationale-free hypotheses block registration and testing.

## 4. Pre-registration & SHA-256 locking
- **Rule H5-04:** On submission, hypothesis text is **immutably locked** — a **SHA-256** of the HYP document is registered in the research registry (Part 5 §2). Modifying a hypothesis post-test to fit data is prohibited and is grounds for termination.
- **MAND:** Lock recorded before any code execution or testing; the locked hash is the version baseline for the hypothesis.
- **Source:** Part 5 §2; Constitution Art. IX; Bill of Rights (Traceability).
- **BLOCK:** No testing on an unregistered/unlocked hypothesis; any post-lock modification blocks the hypothesis and is escalated.

## 5. Ownership & approval status
- **Rule H5-05:** Every hypothesis has a **named owner** (Quant Researcher) and an **approval status**; **pre-testing approval by Head of Research and Lead Statistician** is required before any code execution (Part 5 §2; Part 1 §1.3 roles).
- **MAND:** Owner, status (`PENDING_REVIEW` / `APPROVED` / `REJECTED`), and approval sign-off are recorded; replication owner is identified (HYP-21).
- **Source:** Part 5 §2; Part 1 §1.3.
- **BLOCK:** Unapproved or unowned hypotheses cannot move to testing.

## 6. What makes a hypothesis eligible for testing
- **Rule H5-06:** A hypothesis is eligible for testing only when **all** hold:
  1. All 22 fields present (H5-02) and falsifiable (H5-03).
  2. SHA-256 locked and unmodified (H5-04).
  3. Pre-testing approved by Head of Research and Lead Statistician (H5-05).
  4. Its data (HYP-16) comes from approved Stage 3 quality snapshots; its features (HYP-09) from approved Stage 4 features; acceptance/rejection criteria (HYP-18/19) defined.
- **Source:** Part 5 §1, §2; Stages 3-4.
- **BLOCK:** Any unmet condition blocks testing eligibility.

## 7. What blocks a hypothesis from moving forward
- **Rule H5-07:** A hypothesis is **blocked** from moving forward if: any of the 22 fields are missing; it is unfalsifiable; it is unlocked or has been modified post-lock; it lacks pre-testing approval or a named owner; its data/feature dependencies are not from approved Stages 3/4; or a failure was later masked (retroactive threshold relaxation is prohibited, ADR-001 / Part 7 failure rule).
- **MAND:** Blocking reasons are recorded in the decision log; a hypothesis stays `REJECTED` or `PENDING_REVIEW` until the specific blocker is resolved and re-approved.
- **Source:** Part 5 §2; Part 7 Quality Gate Failure Rule; ADR-001.
- **BLOCK:** Any blocker halts all research, testing, and downstream work on that hypothesis.

---

## How the hypothesis lock works (summary)
1. Researcher drafts the full 22-field HYP document.
2. Submission computes and registers the document's **SHA-256** in the research registry.
3. The locked text is the frozen baseline; **no post-lock edits** are permitted.
4. Head of Research + Lead Statistician grant pre-testing approval before any code runs.
5. Only then may research/testing begin (next governed stage).

## Artifacts that must exist before Stage 6 begins
1. Registered, **SHA-256-locked** HYP document(s) with all 22 fields.
2. Pre-testing approval sign-off (Head of Research + Lead Statistician) and recorded owner/status.
3. Dependencies confirmed: HYP-16 data from approved Stage 3 snapshots; HYP-09 features from approved Stage 4 feature set.
4. Acceptance/rejection criteria (HYP-18/19) and confidence level (HYP-20) recorded.
5. Decision-log entry recording each registered/locked hypothesis.
