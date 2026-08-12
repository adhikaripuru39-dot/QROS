# QROS - Stage 8 Statistical Research Methodology Rule Map

Specification-only. Grounded in Master Handbook Part 8 (plus Parts 2, 7, 9 and the Stage 1-7 packages). Thresholds and mechanics taken verbatim; **no p-hacking, no threshold drift, no retroactive approval** (Part 8 mandate; Part 7 §2; ADR-001).

**MAND** = mandatory; **BLOCK** = what a failure halts.

> **Pipeline reference.** "Pipeline Stage N" below refers to the 15-stage research workflow governed by `STAGE_7_PIPELINE_MAP.md` (Part 7). This map is the statistical-methodology layer that governs how tests at those stages are conducted and judged.

---

## 1. Required statistical tests and where they apply
- **Rule ST8-01:** The following tests are **mandatory** and apply only in their documented domain (Part 8 §1):

| Test | Institutional threshold | Application domain |
| :--- | :--- | :--- |
| Deflated Sharpe Ratio (DSR) | `DSR = P(SR > SR0 \| N_trials, skew, kurt)`; **p-value < 0.01** for backtest acceptance | Evaluating backtest Sharpe ratio subject to trial count N |
| False Discovery Rate (FDR-BH) | `P_(i) <= (i/N) * q*`; target **q* <= 0.05** across feature candidate pool | Screening cross-sectional factor universes |
| Family-Wise Error Rate (FWER-Holm) | `p_(i) <= alpha / (N - i + 1)`; **alpha = 0.01** | Confirmatory hypothesis testing for capital allocation |
| Combinatorial Purged CV (CPCV) | Purging gap = max_holding; Embargo = 1% total sample; **N_paths >= 16; PBO < 0.10** | Cross-validation scheme for non-IID financial time series |
| Stationary Bootstrap (Politis & Romano) | Block resampling with geometric-distributed block lengths to preserve autocorrelation | Non-parametric robustness (Part 8 §2) |
| Permutation Tests | Shuffle feature series **10,000 times**, return targets fixed, empirical null distribution | Non-parametric robustness / p-hacking test (Part 8 §2) |

- **MAND:** Every empirical finding is subjected to multiple-testing adjustments, non-parametric bootstrapping, and p-hacking tests (Part 8 mandate). A test is used only in its documented domain.
- **Source:** Part 8 §1-§2; Part 2 (DSR & p-hacking test).
- **BLOCK:** A result lacking its applicable test, or a test applied outside its domain, is blocked from promotion.

## 2. Multiple-testing control
- **Rule ST8-02:** Multiple comparisons are controlled **at the trial level and at the decision level**. The Experiment Registry records total failed trial runs **N** per hypothesis and passes **N directly into the Deflated Sharpe Ratio calculation** (Part 2; Part 8). No trial iteration is unrecorded; p-values are penalized using FWER (Part 2).
- **MAND:** Every experiment is logged to the Experiment Registry with the trial count, dataset lineage, git commit, feature version, hypothesis ID, and statistical test output required to compute DSR truthfully. The full 17-field experiment record is a downstream Stage 9 / Part 9 dependency and is not used here as an authority to expand Stage 8 scope. DSR is always computed with the true trial count **N**; no selective or omitted trial reporting.
- **Source:** Part 8 §1; Part 2; Stage 9 / Part 9 as downstream dependency only.
- **BLOCK:** Unlogged trials, an incomplete experiment record, or a DSR computed without trial-count adjustment blocks the result.

## 3. False-discovery and family-wise error rules
- **Rule ST8-03:** **FDR-BH** controls the expected proportion of false discoveries in screening contexts: `P_(i) <= (i/N)*q*` with **q* <= 0.05** across the feature candidate pool. **FWER-Holm** strictly controls any single false positive in confirmatory contexts: `p_(i) <= alpha/(N-i+1)` with **alpha = 0.01** (confirmatory hypothesis testing for capital allocation).
- **MAND:** Raw p-values (e.g., p < 0.05) are **never** used for promotion decisions; screening results are FDR-adjusted and confirmatory results are FWER-Holm-adjusted before any conclusion.
- **Source:** Part 8 §1; Part 2.
- **BLOCK:** A decision based on uncorrected p-values, or a confirmatory allocation decision not under FWER-Holm, is blocked.

## 4. Out-of-sample and cross-validation expectations
- **Rule ST8-04:** For non-IID financial time series, validation is performed under **CPCV**: purging gap = max_holding, embargo = 1% total sample, **N_paths >= 16**, and **PBO < 0.10**. Results must also pass the pipeline walk-forward OOS gate: **OOS Sharpe > 2.0, MaxDD < 15%** (Pipeline Stage 11).
- **MAND:** No leakage-contaminated cross-validation; purging and embargo are applied; out-of-sample walk-forward evidence is mandatory before a result moves toward validation.
- **Source:** Part 8 §1; Part 7 §1 (Pipeline Stage 11).
- **BLOCK:** CV without purging/embargo, PBO >= 0.10, or OOS performance below threshold blocks the result.

## 5. Minimum evidence thresholds
- **Rule ST8-05:** The following minimum thresholds are mandatory and **never relaxed** (ADR-001):

| Evidence | Threshold | Source |
| :--- | :--- | :--- |
| DSR p-value (backtest acceptance) | < 0.01 | Part 8 §1 |
| In-sample hypothesis test (Pipeline Stage 9) | t-stat > 3.0, p < 0.001 | Part 7 §1 |
| Feature stationarity (Pipeline Stage 7) | ADF p < 0.05 | Part 7 §1 |
| Multicollinearity (Pipeline Stage 8) | VIF < 10.0 | Part 7 §1 |
| OOS walk-forward (Pipeline Stage 11) | OOS Sharpe > 2.0, MaxDD < 15% | Part 7 §1 |
| Independent replication (Pipeline Stage 12) | match > 99.9% | Part 7 §1 |
| Backtest overfitting (CPCV) | PBO < 0.10 | Part 8 §1 |

- **MAND:** Every result meets **all** applicable thresholds; none is lowered to force a pass.
- **Source:** Part 8 §1; Part 7 §1; ADR-001.
- **BLOCK:** Any unmet threshold blocks the result from promotion.

## 6. Robustness and sensitivity requirements
- **Rule ST8-06:** Results are judged robust only after passing the non-parametric and stress suite: **stationary bootstrap** (Politis & Romano) and **permutation tests** (10,000 shuffles of the feature series with return targets fixed) from Part 8 §2, plus **stable performance across ±50% parameter shift** (Pipeline Stage 10, Part 7 §1).
- **MAND:** The robustness suite is run and logged before any result moves toward validation; sensitivity results are part of the experiment record (EXP-11 Key Metrics, EXP-13 Limitations).
- **Source:** Part 8 §2; Part 7 §1 (Pipeline Stage 10); Part 9 §1.
- **BLOCK:** A result without the robustness suite, or unstable under ±50% parameter shift, is blocked.

## 7. What blocks a result from being promoted
- **Rule ST8-07:** A result is **blocked from promotion toward validation (Pipeline Stage 11) or research approval (Pipeline Stage 14)** unless **all** hold:
  1. The hypothesis is registered, SHA-256-locked, and pre-testing approved (Stage 5; Part 5).
  2. All prior pipeline stage gates passed with formal sign-off (Part 7; P7-01..P7-06).
  3. The applicable tests ran in-domain (ST8-01), multiple-testing corrections applied (ST8-02/ST8-03), OOS/CPCV passed (ST8-04), minimum thresholds met (ST8-05), and robustness passed (ST8-06).
  4. The downstream experiment record fields needed for DSR truthfulness exist in the Experiment Registry; the complete 17-field record is a Stage 9 / Part 9 dependency and is not required as a Stage 8 authority.
  5. No p-hacking, no threshold drift, no retroactive approval (Part 7 §2; ADR-001).
- **MAND:** Blocking reasons are recorded in the decision log; no result is silently dropped or forcibly advanced.
- **Source:** Part 8; Part 7; Part 5; ADR-001; Part 9 only as downstream dependency.
- **BLOCK:** Any unmet condition blocks promotion.

---

## Mandatory statistical evidence (summary)
DSR p < 0.01 for backtest acceptance · FDR-BH q* <= 0.05 in screening · FWER-Holm alpha = 0.01 for confirmatory/capital-allocation · CPCV with purging = max_holding, embargo = 1% sample, N_paths >= 16, PBO < 0.10 · in-sample t-stat > 3.0 / p < 0.001 (Pipeline Stage 9) · OOS Sharpe > 2.0 / MaxDD < 15% (Pipeline Stage 11) · replication > 99.9% (Pipeline Stage 12) · stationary bootstrap + 10,000x permutation robustness.

## How QROS handles multiple comparisons and false discoveries (summary)
Every trial is logged in the Experiment Registry; total trial count N feeds the DSR directly (Part 2 / Part 8). Screening uses FDR-BH (q* <= 0.05); confirmatory decisions use FWER-Holm (alpha = 0.01); raw p-values are never used for promotion. All thresholds are fixed and non-relaxable.

## Conditions before a result moves toward validation
1. Hypothesis registered, locked, and pre-testing approved (Stage 5).
2. All applicable statistical tests run in-domain with corrections (ST8-01..ST8-03).
3. CPCV passed (PBO < 0.10) and walk-forward OOS evidence meets threshold (ST8-04, ST8-05).
4. Robustness suite passed: stationary bootstrap, 10,000x permutation, stable ±50% (ST8-06).
5. Full 17-field experiment record logged (Part 9); no p-hacking, threshold drift, or retroactive approval.

## Artifacts that must exist before Stage 9 begins
1. Approved Stage 8 statistics-rule set (this map) + sign-off.
2. The mandatory statistical tests and their application domains confirmed.
3. Multiple-testing control protocol (DSR with trial count, FDR-BH, FWER-Holm) and CPCV expectations fixed.
4. Robustness suite requirements (stationary bootstrap, 10,000x permutation, ±50% sensitivity) specified.
5. Decision-log entry recording Stage 8 approval.
