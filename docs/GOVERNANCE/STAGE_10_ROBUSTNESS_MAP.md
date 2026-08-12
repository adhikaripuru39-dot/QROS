# QROS - Stage 10 Robustness Testing Rule Map

Specification-only. Grounded in Master Handbook Part 10 (Edge Discovery, false-edge diagnostics) plus Parts 2, 7, 8 and the Stage 1-9 packages. Thresholds and mechanics taken verbatim; **no single-fragile-sample acceptance, no threshold relaxation** (Part 7 §2; Part 10 mandate; ADR-001).

**MAND** = mandatory; **BLOCK** = what a failure halts.

> **Pipeline reference.** "Pipeline Stage N" below refers to the 15-stage research workflow governed by `STAGE_7_PIPELINE_MAP.md` (Part 7). This map is the robustness-testing layer that governs how stress, sensitivity, and regime-shift checks are applied to results.

---

## 1. Parameter stability requirements
- **Rule R10-01:** A result must be **stable across ±50% parameter shift** (Pipeline Stage 10, Part 7 §1). Additionally, performance degradation under **slight perturbation (±10%)** is a **curve-fitting / overfitting diagnostic** (Part 10 §2, diagnostic 1).
- **MAND:** The ±50% stability test is run and passed; the ±10% perturbation test is run to detect curve-fitting. Both results are logged in the experiment record.
- **Source:** Part 7 §1 (Pipeline Stage 10); Part 10 §2 (diagnostic 1).
- **BLOCK:** Instability at ±50% blocks promotion. Sharp degradation at ±10% flags the result as curve-fitted and blocks promotion.

## 2. Sensitivity analysis expectations
- **Rule R10-02:** Sensitivity is measured by **stationary bootstrap** (Politis & Romano — block resampling with geometric-distributed block lengths to preserve autocorrelation, Part 8 §2) and **permutation tests** (shuffle feature series **10,000 times** with return targets fixed to construct an empirical null, Part 8 §2). The **Signal-to-Noise Ratio (SNR)** is assessed under permutation testing — an SNR **statistically indistinguishable from zero** flags the coincidence/luck diagnostic (Part 10 §2, diagnostic 3).
- **MAND:** Bootstrap and 10,000× permutation tests are both run; SNR under permutation is recorded; results are logged.
- **Source:** Part 8 §2; Part 10 §2 (diagnostic 3).
- **BLOCK:** SNR indistinguishable from zero under permutation, or missing bootstrap/permutation suite, blocks promotion.

## 3. Stress testing requirements — five false-edge diagnostics
- **Rule R10-03:** Every candidate signal is evaluated against the **5 False Edge diagnostics** (Part 10 §2 mandate):

| # | Diagnostic | Detection method | Source |
| :- | :--- | :--- | :--- |
| 1 | Curve-Fitting / Overfitting | Performance drops under slight parameter perturbation (±10%) | Part 10 §2; R10-01 |
| 2 | Data Mining / Snooping | DSR fails after adjusting for total tested trial count | Part 10 §2; Part 8 §1 (DSR); Stage 8 ST8-01/ST8-02 |
| 3 | Coincidence / Luck | SNR statistically indistinguishable from zero under permutation testing | Part 10 §2; Part 8 §2 |
| 4 | Execution Mirage | Edge disappears once Level 2 order book spread costs and square-root market impact are subtracted | Part 10 §2; Part 2 (execution bias) |
| 5 | Capacity Bottleneck | Edge exists only for trivial trade sizes (< $10,000) and cannot scale to institutional capital ($50M+) | Part 10 §2 |

- **MAND:** All five diagnostics are run; every triggered diagnostic is logged; no result is accepted with any triggered diagnostic.
- **Source:** Part 10 §2; Part 8 §1 (DSR); Part 2 (execution bias mitigation).
- **BLOCK:** Any triggered false-edge diagnostic blocks promotion.

## 4. Regime-shift / subperiod analysis
- **Rule R10-04:** Results must be verified across **multiple subperiods and stress regimes**. The backtest span must be **multi-decade, encompassing the 2008, 2011, 2020, and 2022 market crises** (Part 2, sampling-bias mitigation). The edge's classification determines its decay half-life and verification metric (Part 10 §1):

| Edge category | Decay half-life | Verification metric (Part 10 §1) |
| :--- | :--- | :--- |
| Structural | Multi-year / long-term persistence | Cointegration test (Engle-Granger) p < 0.001 |
| Behavioral | Months to years | Cross-sectional momentum t-stat > 3.5 across 20-year sample |
| Execution / Microstructure | Sub-second to milliseconds | Execution fill rate advantage over public NBBO |
| Statistical Arbitrage | Weeks to months | Mean-reversion half-life (Ornstein-Uhlenbeck τ < 5 days) |

- **MAND:** No result is accepted on the basis of a single regime; the edge type is named and its Part 10 §1 verification metric applied; the backtest span covers the required crises.
- **Source:** Part 2 (sampling bias); Part 10 §1; Stage 6 G6-04 (regime-awareness).
- **BLOCK:** A single-regime result, missing edge-type verification, or insufficient backtest-span coverage blocks promotion.

## 5. Sample perturbation expectations
- **Rule R10-05:** Sample perturbation is achieved through **CPCV** (purging gap = max_holding, embargo = 1% total sample, N_paths ≥ 16, PBO < 0.10, Part 8 §1), **stationary bootstrap block resampling** (Part 8 §2), and **multi-decade backtest coverage** (Part 2). The result's performance must be consistent across perturbations.
- **MAND:** CPCV is run and logged (PBO recorded); bootstrap is run; backtest span covers the required crises. Performance consistency across perturbation methods is assessed.
- **Source:** Part 8 §1-§2; Part 2.
- **BLOCK:** Missing CPCV, PBO ≥ 0.10, insufficient backtest span, or inconsistent performance across perturbation methods blocks promotion.

## 6. What counts as robustness evidence
- **Rule R10-06:** A result is **robust** only when **all** hold:
  1. Stable across ±50% parameter shift (R10-01).
  2. No sharp degradation at ±10% (R10-01, curve-fitting cleared).
  3. Bootstrap and 10,000× permutation tests passed; SNR distinguishable from zero (R10-02).
  4. All 5 false-edge diagnostics cleared (R10-03).
  5. Verified across multiple subperiods/stress regimes; edge type verified per Part 10 §1 metric (R10-04).
  6. Sample perturbation passed: CPCV PBO < 0.10, multi-decade coverage (R10-05).
- **Source:** Parts 2, 7, 8, 10; ADR-001.
- **BLOCK:** Any unmet condition means robustness is not established.

## 7. What blocks a result from moving forward
- **Rule R10-07:** A result is **blocked from moving toward walk-forward validation (Pipeline Stage 11) or research approval (Pipeline Stage 14)** unless R10-01 through R10-06 all passed with no false-edge trigger, all robustness artifacts are logged in the Experiment Registry (Part 9), and no threshold is relaxed (ADR-001).
- **MAND:** Blocking reasons are recorded in the decision log; no result is silently dropped or force-promoted.
- **Source:** Parts 2, 7, 8, 10; Stage 8 ST8-06/ST8-07; ADR-001.
- **BLOCK:** Any unmet condition blocks promotion.

---

## What robustness means in QROS (summary)
A result is robust when it survives parameter perturbation (±50%, no degradation at ±10%), passes non-parametric resampling (bootstrap + 10,000× permutation), clears all five false-edge diagnostics (curve-fitting, data mining, coincidence/luck, execution mirage, capacity bottleneck), is verified across multiple subperiods and stress regimes (including 2008/2011/2020/2022 crises), and passes sample perturbation (CPCV PBO < 0.10, multi-decade coverage). It is verified against the appropriate edge-classification metric (Part 10 §1). No result is accepted on a single fragile sample.

## Which stress and sensitivity checks are mandatory (summary)
Parameter stability ±50% (pipeline gate) and ±10% (curve-fitting diagnostic) · stationary bootstrap · permutation tests 10,000× · SNR under permutation · five false-edge diagnostics (Part 10 §2) · CPCV (PBO < 0.10) · multi-decade backtest span (2008/2011/2020/2022) · edge-type verification per Part 10 §1 metric.

## How failed robustness is logged and blocked (summary)
Every robustness failure — instability, false-edge trigger, missing suite, or insufficient coverage — is logged in the Experiment Registry (Part 9) and the decision log with its specific diagnostic or rule. The result is blocked from promotion to pipeline Stage 11 (Walk-Forward) or Stage 14 (Approval). Retroactive threshold relaxation is prohibited (ADR-001).

## Artifacts that must exist before Stage 11 begins
1. Approved Stage 10 robustness-rule set (this map) + sign-off.
2. Robustness suite results logged: ±50% stability, ±10% curve-fitting, bootstrap, 10,000× permutation, SNR under permutation.
3. All 5 false-edge diagnostic results logged (triggered or cleared).
4. Regime/subperiod analysis results with edge-type verification and multi-decade coverage logged.
5. CPCV results logged (PBO, N_paths).
6. Decision-log entry recording Stage 10 approval.
