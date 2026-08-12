# QROS - Stage 9 Experiment Tracking Rule Map

Specification-only. Grounded in Master Handbook Part 9 (plus Parts 2, 7, 8 and the Stage 1-8 packages). Record fields and mechanics taken verbatim; **no untracked experimentation, no hidden trials, no retroactive editing** (Part 9 mandate; Bill of Rights Article 1; ADR-001).

**MAND** = mandatory; **BLOCK** = what a failure halts.

---

## 1. Required experiment-record fields
- **Rule T9-01:** Every experiment carries the **complete 17-field record** (Part 9 §1), taken verbatim:

| Field | Identifier | Institutional description (Part 9 §1) |
| :- | :- | :--- |
| EXP-01 | Experiment ID | Globally unique hash (e.g., EXP-20260806-991A04) |
| EXP-02 | Date & Timestamp | ISO 8601 UTC execution timestamp |
| EXP-03 | Researcher Name | Quant Researcher ID and division email tag |
| EXP-04 | Dataset Version Hash | SHA-256 hash of exact dataset snapshot used |
| EXP-05 | Code Version / Git Commit | Full 40-character Git commit hash |
| EXP-06 | Feature Version | Feature Store version string (e.g., feat_v2.4.1) |
| EXP-07 | Hypothesis ID | Foreign key linking to registered HYP document |
| EXP-08 | Objective | Primary optimization/validation target (e.g., Maximizing DSR) |
| EXP-09 | Hyperparameter Map | Complete JSON dictionary of all hyperparameters |
| EXP-10 | Statistical Test Output | Recorded t-stat, p-value, DSR score, and Sharpe Ratio |
| EXP-11 | Key Metrics | In-Sample & Out-of-Sample Sharpe, Max DD, Turnover % |
| EXP-12 | Conclusions | Structured text summary of empirical findings |
| EXP-13 | Limitations | Identified edge constraints (e.g., high execution sensitivity) |
| EXP-14 | Next Actions | Action items (e.g., promote to Walk-Forward CV or Reject) |
| EXP-15 | Approval Status | Workflow state (PENDING_REVIEW, APPROVED, REJECTED) |
| EXP-16 | Peer Review Notes | Audit comments from Lead Statistician / Peer QR |
| EXP-17 | Replication Status | Verification indicator from independent replication run |

- **MAND:** All 17 fields are present and completed for every experiment; no field is invented, dropped, or left as a placeholder.
- **Source:** Part 9 §1; Code of Scientific Conduct Principle 4.
- **BLOCK:** A record missing any required field is incomplete and blocked from acceptance.

## 2. Git commit and dataset snapshot linkage
- **Rule T9-02:** Every experiment is bound to the **exact inputs that produced it**: EXP-04 is the SHA-256 hash of the exact dataset snapshot used; EXP-05 is the full 40-character git commit of the code repository (Part 9 §1).
- **MAND:** An experiment without both a dataset-snapshot hash and a git commit has no reproducible input lineage and cannot be accepted.
- **Source:** Part 9 §1; Bill of Rights Article 1 (complete dataset references, software version).
- **BLOCK:** Missing or mismatched snapshot/commit linkage blocks acceptance.

## 3. Seed, parameters, and environment capture
- **Rule T9-03:** Every experiment captures its full configuration: EXP-02 (ISO 8601 UTC timestamp), EXP-06 (feature version), EXP-08 (objective), and EXP-09 (complete JSON hyperparameter map), plus random seeds and execution environment as required for reproducibility (Bill of Rights Article 1).
- **MAND:** No default or omitted parameter map; seeds and environment are recorded whenever applicable to the result.
- **Source:** Part 9 §1; Bill of Rights Article 1 (configuration, parameters, random seeds, execution environment, date and time, author).
- **BLOCK:** A record without complete parameter/seed/environment capture blocks acceptance.

## 4. Trial counting and failed-attempt logging
- **Rule T9-04:** The Experiment Tracker records **total failed trial runs N per hypothesis** and passes **N directly into the Deflated Sharpe Ratio calculation** (Part 9 §2). Every trial iteration — including failed attempts — is logged; p-values are penalized using FWER (Part 2). Failed experiments are documented, not hidden (Bill of Rights Article 4).
- **MAND:** Trial count N is complete and truthful; no trial is omitted, selective, or back-filled; EXP-12 (Conclusions) and EXP-14 (Next Actions) reflect failed and rejected runs.
- **Source:** Part 9 §2; Part 2; Bill of Rights Article 4; Stage 8 ST8-02.
- **BLOCK:** Hidden or unlogged trials, or a DSR computed without the true N, block acceptance and cascade to Stage 8 promotion rules.

## 5. Artifact retention and traceability
- **Rule T9-05:** Model binaries, feature importance plots, and residual time series are stored in **immutable WORM (write-once-read-many) object storage** (Part 9 §2). The record is **append-only**; no deletion, overwrite, or back-dating. Retention follows Constitution Article IX (document, version, archive).
- **MAND:** Artifacts referenced by EXP-10..EXP-13 exist, are immutable, and are traceable to the experiment ID; no artifact is destroyed or edited.
- **Source:** Part 9 §2; Constitution Article IX.
- **BLOCK:** Mutable, deleted, or unarchived artifacts block acceptance.

## 6. Decision-log / registry cross-linking
- **Rule T9-06:** Every experiment is cross-linked to its context: EXP-07 (hypothesis foreign key to the HYP registry), EXP-03 (researcher), EXP-15 (approval status: PENDING_REVIEW / APPROVED / REJECTED), EXP-16 (peer review notes), and EXP-17 (replication status). Gate failures and blocking reasons are recorded in the Experiment Registry and the decision log (Part 7 §2).
- **MAND:** No orphan records; every acceptance/rejection is traceable to its hypothesis, approval state, peer review, and decision-log entry.
- **Source:** Part 9 §1; Part 7 §2; Constitution Article IX; Stage 8 ST8-07.
- **BLOCK:** An unlinked or orphan experiment record blocks acceptance.

## 7. What blocks an experiment from being accepted
- **Rule T9-07:** An experiment is **not accepted** unless **all** hold:
  1. The complete 17-field record exists and is accurate (T9-01).
  2. Dataset SHA-256 snapshot and 40-character git commit are linked (T9-02).
  3. Seeds, parameters, and environment are fully captured (T9-03).
  4. Trial count N — including failed attempts — is logged and feeds the DSR (T9-04).
  5. Artifacts are retained immutably in WORM storage (T9-05).
  6. Hypothesis, approval status, peer review, and decision-log entries are cross-linked (T9-06).
  7. No hidden trial, no retroactive edit, no hand-logged or unlogged run, and no approval claim.
- **MAND:** Rejection reasons are recorded in the decision log; no experiment is silently dropped or force-accepted.
- **Source:** Part 9; Part 7; Part 8; Bill of Rights Article 1; ADR-001.
- **BLOCK:** Any unmet condition blocks acceptance.

---

## What must be recorded for every experiment and trial (summary)
The complete 17-field EXP record (EXP-01..EXP-17); total trial count N including every failed attempt; the DSR trial-count linkage; and immutable WORM artifacts (model binaries, feature importance plots, residual time series).

## How QROS links experiments to dataset snapshots and git commits (summary)
EXP-04 = SHA-256 hash of the exact dataset snapshot used; EXP-05 = full 40-character git commit of the code repository; EXP-07 binds the experiment to its registered hypothesis. Without both hashes the record has no reproducible input lineage.

## What makes an experiment record complete (summary)
All 17 fields accurate and complete; snapshot + git + hypothesis linkage; seed/parameter/environment capture; truthful trial count N with failed attempts logged; immutable retention; peer review and approval status recorded; cross-linked to the decision log.

## Artifacts that must exist before Stage 10 begins
1. Approved Stage 9 tracking-rule set (this map) + sign-off.
2. The mandatory 17-field EXP record and its required linkages confirmed.
3. Trial-count and failed-attempt logging protocol (N → DSR) fixed.
4. Immutable WORM retention and decision-log/registry cross-linking requirements specified.
5. Decision-log entry recording Stage 9 approval.
