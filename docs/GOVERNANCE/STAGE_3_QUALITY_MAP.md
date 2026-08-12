# QROS - Stage 3 Quality-Rule Map

Specification-only. Each rule names its mandatory check, threshold, governing source, and the downstream work it blocks on failure. Thresholds are taken verbatim from Master Handbook Parts 1-3; none may be relaxed (ADR-001 single source of truth).

Legend: **MAND** = mandatory for all datasets; **BLOCK** = what a failure halts.

---

## 1. Completeness
- **Rule M3-01:** Grid-continuity audit comparing expected exchange session minutes against observed timestamps (Part 2 §1.1).
- **MAND:** No unresolvable gaps; every expected trading minute accounted for or explicitly flagged.
- **Threshold:** Alert (and gate) if missing-bar fraction exceeds **0.05%** of the daily universe (Part 2 §1.1).
- **Source:** Part 2 §1.1; Code of Conduct Principle 3 (completeness).
- **BLOCK:** Any feature/hypothesis/backtest build on the dataset; promotion to production/feature store.

## 2. Timestamp integrity
- **Rule M3-02:** All timestamps in **UTC nanoseconds**; dual-timestamping Event Time vs Knowledge/Release Time (Part 1 §1.2, §4.2; Part 2 §1.4).
- **MAND:** `Knowledge_Timestamp >= Event_Timestamp` on every record (Part 1 §4.2 Point-in-Time Audit); UTC-ns consistency across all rows.
- **Source:** Part 1 §1.2, §4.2; Part 2 §1.4 (IANA tz, venue session calendars, holiday/DST handling).
- **BLOCK:** Any dataset with a timestamp-integrity violation; all downstream research use.

## 3. Duplicate detection
- **Rule M3-03:** Multi-column hash uniqueness on `(Symbol, Timestamp, Open, High, Low, Close, Volume)` (Part 2 §1.3).
- **MAND:** Zero unresolved duplicate candles/stale quotes; dedupe retains the latest hardware receive timestamp (Part 2 §1.3).
- **Source:** Part 2 §1.3.
- **BLOCK:** Duplicate-contaminated datasets; downstream feature/hypothesis work.

## 4. Bad-tick suppression
- **Rule M3-04:** Rolling Median Absolute Deviation (MAD) filter, `|P_t - M_med| / MAD > 8.0`; cross-venue arbitration against a secondary independent feed (Part 2 §1.2; Part 1 §5.1 Case 2).
- **MAND:** Every bad tick suppressed (replaced by previous valid mid) and flagged `BAD_TICK_SUPPRESSED`; non-firm/form-T/canceled codes filtered (Part 1 §4.2; Part 2 §1.2).
- **Source:** Part 1 §4.2, §5.1; Part 2 §1.2.
- **BLOCK:** Backtesting/feature work on un-suppressed data; production promotion.

## 5. Missing-data handling
- **Rule M3-05:** Zero-order-hold forward-fill for illiquid quotes; missing bar volume strictly **0**; **linear interpolation on price is prohibited** (introduces look-ahead) (Part 2 §1.1).
- **MAND:** Every missing value explicitly resolved (ZOH or explicit NULL flag); **no interpolation** on any price series.
- **Source:** Part 2 §1.1.
- **BLOCK:** Any dataset with unresolved or interpolated missing values; downstream research.

## 6. Point-in-time / no-lookahead
- **Rule M3-06:** Bitemporal access; models/signals restricted to Knowledge Time (Part 1 Rule 3; Part 2 §2 Look-Ahead Bias).
- **MAND:** `Knowledge_Timestamp <= Backtest_Execution_Timestamp` on every record (Part 2 §2); bitemporal query syntax enforced (Part 1 Rule 3).
- **Additional (Part 4-linked, flagged for Stage 4):** no global full-sample fitting for scaling — all normalization parameters backward-looking (Part 4 §1.2). **Stage 4 entry requires this to be adopted.**
- **Source:** Part 1 Rule 3; Part 2 §2; Part 4 §1.2 (forward reference).
- **BLOCK:** Any look-ahead contamination blocks all research and execution use of the dataset.

## 7. Provenance & correction rules
- **Rule M3-07:** Raw payloads are **sacrosanct** (never modified, cold-archived); derived data version-controlled with deterministic **SHA-256**; overwriting historical rows is illegal (Part 1 §5.2 Rules 1-2).
- **MAND:** Every dataset carries an Arrow metadata contract (git commit, ETL version, schema version, ingestion timestamp); corrections are appended, never in-place (Part 3 §1.3; Part 1 Rule 2).
- **Corrections:** splits/dividends cross-validated against **two** independent vendors (Part 1 §4.2); futures rollovers via 4 documented methods (Part 2 §1.6); vendor close-price discrepancies flagged at > **1 basis point** (Part 2 §1.5).
- **Source:** Part 1 §4.2, §5.2; Part 2 §1.5, §1.6; Part 3 §1.3.
- **BLOCK:** Any dataset lacking provenance/lineage or correction history; downstream research and reproducibility (Bill of Rights: Reproducibility).

## 8. Approval thresholds
- **Rule M3-08:** A dataset is approved only when it passes **all** mandatory checks M3-01..M3-07 and is signed off by Data Engineer **and** Data Governance Officer (Part 1 §1.3; Part 2 §3.2 QC checklist; Part 1 §4.2).
- **MAND:** Sign-off recorded; dataset eligible for freeze/snapshot only after approval (Part 3 §2.2 snapshot registry).
- **Source:** Part 1 §1.3, §4.2; Part 2 §3.2; Part 3 §2.2.
- **BLOCK:** No dataset is promoted to production/feature store, frozen, or handed to Stage 4 feature work without this approval.

---

## Downstream block summary (what failures stop)
| Failure | Blocks |
| :--- | :--- |
| Any M3-01..M3-08 failure | Feature work, hypothesis work, edge discovery, backtesting, execution |
| Unapproved dataset | Freeze for experimentation; promotion to production/feature store; Stage 4 entry |
| Threshold relaxation (any) | Immediate halt; return to re-validation (Part 7 failure rule; ADR-001) |

## Artifacts that must exist before Stage 4 begins
1. Approved Stage 3 quality-rule set (this map) + sign-off.
2. Per-dataset mandatory-check pass report (M3-01..M3-08).
3. Provenance/lineage record and correction log for each approved dataset.
4. Approved, frozen snapshot(s) registered (Part 3 §2.2), ready for Stage 4 feature work.
