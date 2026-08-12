# QROS - Stage 4 Feature-Rule Map

Specification-only. Rules are grounded in Master Handbook Part 4 (plus Parts 1-3 and Stage 3 quality rules). Thresholds are taken verbatim and must not be relaxed (ADR-001). A feature set is approved only when every rule passes.

**MAND** = mandatory; **BLOCK** = what a failure halts.

---

## 1. Approved feature categories
- **Rule F4-01:** Features are restricted to the approved Part 4 taxonomy (Part 4 §2). Approved categories:
  - Log Returns & Volatility
  - Order Book Imbalance (OBI)
  - Volume-Weighted Average Price (VWAP)
  - Garman-Klass Volatility
  - Microstructure VPIN
  - Cross-Asset Relative Momentum
  - Gamma Exposure (GEX)
- **MAND:** Any feature outside the taxonomy requires a documented amendment (Constitution Art. XI) before use.
- **Source:** Part 4 §2.
- **BLOCK:** Unapproved feature categories block feature-set approval and all downstream research.

## 2. Stationarity & normalization expectations
- **Rule F4-02:** Every feature series must be **stationary**: Augmented Dickey-Fuller **p < 0.05** (Part 4 §3).
- **Rule F4-03:** Normalization uses **Z-score** `z = (x - mu_w)/sigma_w` on a strictly backward-looking window `w`, or **percentile-rank** mapping via expanding/rolling empirical CDF (Part 4 §1.2).
- **MAND:** Log returns and fractional differentiation (`fracdiff d in [0,1]`) are the sanctioned transformations to reach stationarity (Part 4 §1.1).
- **Source:** Part 4 §1.1, §1.2, §3.
- **BLOCK:** Any non-stationary feature (ADF p >= 0.05) blocks feature-set approval and research.

## 3. Leakage & look-ahead prevention
- **Rule F4-04:** **No global/full-sample fitting** — never standardize using full-sample mean/variance; all parameters backward-looking (Part 4 §1.2 "ZERO LOOK-AHEAD SCALING").
- **Rule F4-05:** **No linear interpolation on price** (introduces future leakage; Stage 3 M3-05). Missing data resolved via Stage 3 rules only.
- **MAND:** Every feature uses only data observable at time t (point-in-time; Stage 3 M3-06). No feature encodes future values.
- **Source:** Part 4 §1.2; Part 2 §1.1; Stage 3 M3-05/M3-06.
- **BLOCK:** Any leakage or look-ahead contamination blocks the feature set and all downstream use.

## 4. Rolling-window conventions
- **Rule F4-06:** All windowed parameters (mean, std, CDF, fracdiff memory) are computed on **expanding or rolling backward-looking** windows only (Part 4 §1.2).
- **MAND:** Window size `w` and expansion/rolling choice are declared per feature and recorded in provenance.
- **Source:** Part 4 §1.1, §1.2.
- **BLOCK:** Any feature using forward or centered windows blocks approval.

## 5. Target / label separation
- **Rule F4-07:** Feature computation and target/label definition are kept **strictly separate**. Features never read the target; labels are defined over forward returns using point-in-time knowledge (Part 4 taxonomy; Part 5 HYP-09/HYP-10).
- **MAND:** Feature set records which fields are features vs targets; no target-derived quantity enters feature computation.
- **Source:** Part 4 §2; Part 5 (HYP-09, HYP-10 — forward reference).
- **BLOCK:** Any feature that encodes the target blocks approval and any later hypothesis work.

## 6. Provenance & reproducibility
- **Rule F4-08:** Every feature is recorded with source snapshot (Stage 3 M3-08), mathematical definition, parameters, window convention, and version; reproducible from frozen snapshots (Part 3 §2.2; Bill of Rights: Reproducibility).
- **MAND:** Feature provenance ties back to an approved, quality-checked snapshot; feature set is re-buildable from that snapshot alone.
- **Source:** Part 3 §2.2, §1.3; Part 4 §3; Bill of Rights Art. 1.
- **BLOCK:** Any feature lacking provenance blocks approval and research.

## 7. Approval thresholds & blocking conditions
- **Rule F4-09:** A feature set is approved only when **all** of: ADF p < 0.05 (F4-02); VIF < 10.0 **or** correlation < 0.85 for redundancy (Part 4 §3); SHAP importance positive and stable across out-of-sample walk-forward partitions (Part 4 §3); traceable to approved data foundation and Stage 3 quality rules (Charter §8).
- **MAND:** Feature-set approval is recorded with sign-off; no feature set is promoted without it.
- **Source:** Part 4 §3; Charter §3, §8; ADR-001.
- **BLOCK:** Failure of any threshold blocks feature-set approval and all downstream research.

---

## Allowed transformations (summary)
Log returns · fractional differentiation (fracdiff) · Z-score (backward rolling) · percentile-rank (expanding/rolling) · the 7 approved taxonomy features.

## Forbidden transformations (summary)
Global/full-sample scaling · linear interpolation on price · any feature needing future data · any feature encoding the target · any transformation outside the approved taxonomy without amendment.

## Artifacts that must exist before Stage 5 begins
1. Approved Stage 4 feature-set specification + sign-off.
2. Per-feature provenance record (source snapshot, definition, params, window, version).
3. Stationarity & multicollinearity pass report (ADF p, VIF/corr) on all approved features.
4. Target/label separation note for the feature set.
5. Feature-store contract spec (online/offline parity; Part 3 §2.3), tied to approved frozen snapshots.
