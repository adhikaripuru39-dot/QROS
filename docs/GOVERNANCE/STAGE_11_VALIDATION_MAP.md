## Stage 11 – Walk‑Forward Validation Rule Map

**Purpose** – This rule map enumerates the concrete validation conventions, thresholds, artefacts, and gating conditions that govern the Walk‑Forward Validation stage of QROS. It is referenced by the Charter, Checklist, Scope, and the Governance Board to enforce compliance before any result may progress to Stage 12.

---

### 1. Window Conventions (Rolling‑Window Mechanics)
| Parameter | Definition | Default Value | Allowed Range | Config Key |
|-----------|------------|---------------|---------------|------------|
| **Training window length** | Number of chronological periods (e.g., days, weeks) used to fit the model. | 252 days (≈1 year) | 30 – 1095 days | `training_window_length`
| **Validation window length** | Size of the out‑of‑sample period immediately following the training window. | 63 days (≈3 months) | 21 – 252 days | `validation_window_length`
| **Step size** | Increment by which the windows are shifted forward after each iteration. | 63 days (same as validation length) | ≥ 1 day | `step_size`
| **Test window (optional)** | Final, non‑overlapping window used for a final performance quote before Stage 12. | 63 days | 21 – 252 days | `test_window_length`
| **Calendar alignment** | Rules for handling month‑ends, holidays, or non‑trading days. | Align to first business day of month. | Customizable via `calendar_alignment` | `calendar_alignment`

All parameters **must** be defined in `validation_config.yaml` and version‑controlled. Any change after a validation run requires a new validation request and re‑approval.

---

### 2. Embargo, Purging, and Leakage Prevention
| Rule | Description | Enforcement Mechanism |
|------|-------------|----------------------|
| **Embargo period** | A buffer of `embargo_length` days after the end of the training window that is excluded from both training and validation to remove look‑ahead bias. | Data query excludes embargo dates; enforced by `Data Steward`.
| **Purging** | Remove any data points that may have been used for feature engineering after the start of the training window (e.g., target leakage). | Automated script verifies no future‑looking features are present; checksum logged.
| **No forward‑looking labels** | Labels for the validation window must be derived exclusively from data within that window. | Validation code checks timestamp of label generation; any violation aborts run.
| **Immutable snapshots** | Both training and validation windows are stored as immutable, write‑once files with SHA‑256 hashes recorded. | Audit log verifies hash matches recorded value before any downstream use.

---

### 3. Train / Validation / Test Split Rules
1. **Training data** – All data up to the start of the embargo period.
2. **Validation data** – Data after the embargo period and up to the end of the validation window.
3. **Test data** – Optional final window, never used for model selection; only for final performance reporting.

All splits must be **chronological**; no random shuffling is permitted in Stage 11.

---

### 4. Regime‑Aware Validation Expectations
| Regime | Criteria for identification | Required validation adjustments |
|--------|------------------------------|---------------------------------|
| **High volatility** | VIX > 30 or realized volatility > 2 % / day. | Minimum Sharpe ≥ 1.0; max drawdown ≤ 15 %.
| **Low volatility** | VIX ≤ 15. | Sharpe ≥ 0.8; drawdown ≤ 10 %.
| **Liquidity‑constrained** | Average daily volume < 500k shares. | Transaction cost model applied; turnover ≤ 30 %.
| **Regime‑neutral** | Neither high nor low volatility thresholds met. | Use baseline thresholds (Sharpe ≥ 0.9, drawdown ≤ 12 %).

The `RegimeClassifier` must be run on each validation window and its label stored in the `validation_log.json`.

---

### 5. Out‑of‑Sample Acceptance Thresholds
| Metric | Target (must be met or exceeded) | Statistical Test | Significance Level |
|--------|---------------------------------|----------------|--------------------|
| **Sharpe ratio** | ≥ 1.0 (high‑vol), ≥ 0.9 (neutral), ≥ 0.8 (low‑vol) | One‑sample t‑test against null Sharpe = 0.5 | p < 0.05 |
| **Maximum drawdown** | ≤ 15 % (high‑vol), ≤ 12 % (neutral), ≤ 10 % (low‑vol) | None (hard limit) | N/A |
| **Sortino ratio** | ≥ 1.5 | One‑sample test vs. 1.0 | p < 0.05 |
| **Information ratio** | ≥ 0.5 | None | N/A |
| **Stability metric** (e.g., correlation of returns across windows) | ≥ 0.7 | Pearson correlation test | p < 0.01 |

All thresholds are **hard gating** – if any metric fails, the result is **rejected** and cannot proceed.

---

### 6. Required Validation Artifacts & Logs
1. **`validation_config.yaml`** – Full configuration used for the run (archived with checksum).
2. **Data snapshots** – `train_<timestamp>.parquet` and `val_<timestamp>.parquet` (immutable, SHA‑256 recorded).
3. **`validation_log.json`** – JSON file containing:
   - Window start/end dates.
   - Regime label.
   - Metrics values.
   - Random seed, library versions, environment details.
4. **Metrics report** – `metrics_report.pdf` and `metrics_report.csv` summarising all metrics per window and aggregated.
5. **Signed Validation‑Rule Map** – This document signed by Validation Owner and Compliance Officer, stored as `validation_rule_map_<timestamp>.pdf`.
6. **Peer‑review sign‑off forms** – PDF scans of two senior researcher approvals.
7. **Audit ledger entry** – Append to central `audit.log` with timestamps, checksums, and signer IDs.

All artefacts must be stored in `artifacts/validation/` on write‑once, read‑many (WORM) storage.

---

### 7. Do‑Not‑Proceed List (Blocking Conditions)
The following conditions *automatically block* any downstream Stage 12 activities, strategy implementation, uncontrolled back‑testing, execution, or approval claims:

1. **Missing or mismatched artefacts** – Any file listed in Section 6 is absent, corrupted, or has a checksum mismatch.
2. **Threshold violation** – Any acceptance metric in Section 5 fails to meet its target or statistical significance.
3. **Leakage detected** – Embargo or purging rules are violated, or forward‑looking features are found in the training set.
4. **Regime classification failure** – Regime label cannot be determined or falls outside the defined set.
5. **Unsigned validation‑rule map** – The map is not signed by both the Validation Owner and the Compliance Officer.
6. **Incomplete checklist** – Any item in `STAGE_11_CHECKLIST.md` remains unchecked after final review.
7. **Unauthorized configuration change** – `validation_config.yaml` altered after a run without a new validation request.
8. **Execution of any trading logic** – Presence of order‑dispatch code, live‑trading APIs, or execution hooks in the submitted model.
9. **Strategy code changes** – Modifications to strategy parameters or logic not approved in earlier stages (Stages 1‑10).
10. **Unapproved back‑testing** – Running any back‑test outside the walk‑forward framework (e.g., full‑sample or overlapping windows).

**If any item on this list is true, the result MUST be rejected, the compliance officer must record the rejection, and the pipeline must halt.**

---

### 8. Governance Review & Sign‑Off
| Role | Signature | Date |
|------|-----------|------|
| **Validation Owner** | _______________________ | ________ |
| **Compliance Officer** | _______________________ | ________ |
| **Research Lead (Submitter)** | _______________________ | ________ |
| **Peer Reviewer 1** | _______________________ | ________ |
| **Peer Reviewer 2** | _______________________ | ________ |

All signatures must be captured electronically; the signed PDF becomes the immutable `validation_rule_map_<timestamp>.pdf` referenced in the Checklist.

---

**Version History**
- v1.0 – 2026‑08‑12 (initial governance package draft)

---

*This rule map is the authoritative source for Stage 11 walk‑forward validation. Any deviation must be documented, justified, and approved by the Governance Board before proceeding.*