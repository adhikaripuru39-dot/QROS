# QROS Strict Compliance Edge Validation & Legacy Code Audit

**Document ID:** `QROS-AUDIT-EDGE-001`  
**Mission:** QROS Strict Compliance Edge Validation  
**Authority:** QROS Project Manager / Architecture Authority  
**Date:** 2026-08-15  
**Target Legacy Modules:**  
- `src/qros/edges/taxonomy.py`  
- `src/qros/edges/audit.py`  
- `tests/test_edges.py`  
**Comparative Governance Baseline:**  
- `src/qros/governance/policy.py`  
- `src/qros/pipeline/stages.py`  
- `src/qros/schemas/validation_profile.py`  
- `src/qros/pipeline/evaluation.py`  
- `src/qros/pipeline/costs.py`  
- `src/qros/tracking/ledger.py` ($K = 119$)  
- `src/qros/stats/bootstrap.py` (Politis & Romano 1994 Stationary Block Bootstrap)  
- `src/qros/data/vault/oos_vault.py` (Tier-4 Protected OOS Firewall)  

---

## 1. Executive Summary

This compliance audit evaluates the legacy edge logic in `src/qros/edges/` to determine whether it can be admitted into the active QROS quantitative research pipeline under current institutional governance.

### Core Verdict:
> [!CAUTION]
> **CAN THIS LEGACY EDGE LOGIC BE ADMITTED INTO THE NEW QROS WITHOUT VIOLATING STRICT COMPLIANCE?**  
> **ANSWER: NO.**  
> The legacy edge modules cannot be admitted into the active research pipeline. While the modules reflect structured conceptual intent, the underlying implementation contains **fatal mathematical flaws**, **vulnerability to input gaming**, **naive execution/capacity heuristics**, and **complete disconnection from the central multiple-testing trial ledger and pre-registration schemas**.

---

## 2. Legacy Module Deep-Dive Audit

### 2.1 Module 1: `src/qros/edges/taxonomy.py`

#### What It Does & Assumes:
- Defines `EdgeCategory` (`STRUCTURAL`, `BEHAVIORAL`, `EXECUTION`, `STAT_ARB`, `UNCLASSIFIED`).
- Defines `EdgeSpec` with static descriptive strings.
- Implements `classify_edge(cointegration_p, momentum_t, ou_half_life, latency_advantage) -> EdgeClassification`.
- Assumes that if a caller supplies an arbitrary scalar meeting a threshold (e.g., `cointegration_p < 0.001`), the candidate is categorized with `"high"` confidence.

#### What It Can and Cannot Prove:
- **Can Prove:** Categorizes caller-provided floating-point numbers into string Enum tags.
- **Cannot Prove:** Does **NOT** prove the existence of an edge. It performs no statistical computation, accepts naked floats without examining underlying time-series, and verifies no statistical power or sample length.

#### Governance & Vulnerability Findings:
1. **Input Abuse & Caller Control:** The function accepts raw scalars directly from the caller. A user can pass `classify_edge(cointegration_p=0.0001)` without providing any actual price data, yielding a `"high"` confidence structural classification.
2. **Missing Pre-Registration Discipline:** Disconnected from `HypothesisRecord`, `ValidationProfile`, and empirical quality gates.
3. **Superseded by Institutional Architecture:** In modern QROS governance (`QROS-STD-VAL-001`), empirical research is classified by **Class-Calibrated Validation Profiles** (Classes I–V) with explicit sample size, calendar span, transaction cost multipliers, and bootstrap embargo rules.

---

### 2.2 Module 2: `src/qros/edges/audit.py`

#### What It Does & Assumes:
- Implements `audit_false_edge(returns, n_trials, perturbed_returns, execution_slippage_bps, tiny_size_pnl, institutional_size_pnl, ...)` returning `EdgeAudit`.
- Implements 5 mandatory diagnostics:
  1. `curve_fitting`: Parameter-perturbation degradation check ($< 10\%$).
  2. `data_mining`: Deflated Sharpe Ratio adjusted for `n_trials`.
  3. `coincidence`: 2-sample permutation test comparing first half to second half of returns.
  4. `execution_mirage`: Net return after slippage subtraction ($> 0$).
  5. `capacity_bottleneck`: Ratio of institutional PnL to tiny PnL ($> 50\%$).

#### Fatal Scientific Flaws & Compliance Breaches:

1. **Fatal Flaw in Coincidence / Permutation Test (Mathematically Inverted Logic):**
   - The code splits the sample in half (`returns[:half]` vs `returns[half:]`) and requires $p < 0.05$ on the difference of means:
     ```python
     perm = permutation_test(returns[:half], returns[half:], lambda a, b: float(np.mean(a) - np.mean(b)))
     passed_perm = perm["p_value"] < 0.05
     ```
   - **Why this is catastrophic:** A $p < 0.05$ on a two-sample test means the first half and second half are **statistically significantly DIFFERENT** (i.e. the strategy is **NON-STATIONARY**, regime-dependent, or experiencing structural break).
   - A true, robust edge requires temporal stationarity (i.e. $p > 0.05$, failing to reject the null of identical distributions). Requiring $p < 0.05$ **actively forces the audit to select for unstable regime shifts**.
   - Furthermore, naive permutations destroy time-series autocorrelation and volatility clustering, violating the Politis & Romano (1994) Stationary Block Bootstrap standard enforced by modern QROS.

2. **Trial Count Gaming ($n\_trials$ Vulnerability):**
   - `audit_false_edge` accepts `n_trials: int` directly as a parameter from the caller.
   - The caller can run 500 exploratory backtests and simply pass `n_trials=1` or `n_trials=2` (as demonstrated in `tests/test_edges.py`), bypassing multiple-testing deflated Sharpe ratio adjustments.
   - In modern QROS, $K$ is centrally and immutably enforced via `GLOBAL_TRIAL_LEDGER.json` ($K = 119$).

3. **Trivial Curve-Fitting Bypass:**
   - The check computes `degradation = abs(pert_mean - base_mean) / abs(base_mean) < 0.10`.
   - In `tests/test_edges.py`, the test passes by setting `perturbed = r * 0.98`. Linearly multiplying returns by a constant is an arithmetic scaling, NOT an empirical parameter perturbation (such as shifting lookback windows by $\pm 20\%$).
   - This check completely misses variance explosions, drawdown expansions, or skewness decay under true parameter perturbations.

4. **Naive Execution & Friction Modeling:**
   - Evaluates `net = mean_return_bps - execution_slippage_bps > 0`.
   - Ignores dynamic bid/ask spread variation, volatility widening, latency drift, overnight financing/swaps, and market maker spread multipliers ($1.5\times - 2.5\times$) enforced by `TransactionCostModel`.

5. **Cosmetic Capacity Check:**
   - Evaluates `institutional_size_pnl / tiny_size_pnl > 0.5`.
   - Accepts arbitrary float literals from the caller with zero underlying market impact modeling (e.g. Almgren-Chriss or square-root law of market impact).

---

### 2.3 Module 3: `tests/test_edges.py`

#### What It Does & How It Tests:
- Tests the contract of `EDGE_TAXONOMY` and `audit_false_edge`.
- Employs synthetic Gaussian data and hand-crafted fixtures.

#### Vulnerability Findings:
- In `test_fully_evidenced_audit_passes_only_when_all_five_pass`, the test suite constructs an artificial two-regime series (`rng.normal(0.006, 0.01, 150)` followed by `rng.normal(0.001, 0.01, 150)`) specifically to force a mean difference and trigger $p < 0.05$ on the broken permutation test.
- It supplies `n_trials=2`, `perturbed = r * 0.98`, and hardcoded PnL values (`1000.0` and `60_000.0`).
- While this proves the Python functions execute without syntax errors, it demonstrates how easily the legacy audit can be fooled by artificial, scientifically invalid inputs.

---

## 3. Comparative Governance Analysis

| Dimension | Legacy Edge Package (`src/qros/edges`) | Current QROS Governance Architecture | Compliance Assessment |
| :--- | :--- | :--- | :--- |
| **Research Classification** | Static 4-category taxonomy Enum (`EdgeCategory`) | 5 Class-Calibrated Validation Profiles (`CLASS-I` to `CLASS-V`) | **NON-COMPLIANT** (Legacy is static vocabulary) |
| **Statistical Validation** | Naive DSR + Inverted 2-sample permutation test | 6-Gate Battery: Moments, Net PF, Net SR, DSR ($K=119$), Stationary Block Bootstrap 95% CI | **FATALLY FLAWED** (Inverted permutation logic) |
| **Multiple Testing** | Caller-passed `n_trials` scalar | Centralized, monotonic `GlobalTrialLedger` (`GLOBAL_TRIAL_LEDGER.json`) | **NON-COMPLIANT** (Vulnerable to caller gaming) |
| **Execution Friction** | Scalar slippage subtraction (`net_bps > 0`) | `TransactionCostModel` with dynamic spreads, slippage multipliers ($1.5\times-2.5\times$), latency delay, swaps | **NON-COMPLIANT** (Unrealistically naive) |
| **Parameter Stability** | Single mean degradation check ($< 10\%$) | Multi-dimensional perturbation grids ($\pm 15\% - \pm 40\%$), plateau stability, bootstrap bounds | **NON-COMPLIANT** (Easily bypassed) |
| **Out-of-Sample Isolation** | No OOS partitioning or vault integration | Firewalled Tier-4 Protected OOS Vault with cryptographic SHA-256 manifest | **NON-COMPLIANT** (Missing data lineage) |

---

## 4. Module Dispositions

1. **`src/qros/edges/taxonomy.py` $\to$ `ARCHIVE`**
   - *Rationale:* Useful only as historical documentation of Part 10 concept definitions. Superseded by `src/qros/schemas/validation_profile.py` and `src/qros/schemas/hypothesis.py`. Must NOT be imported into active research pipelines.
2. **`src/qros/edges/audit.py` $\to$ `REJECT`**
   - *Rationale:* Contains fundamentally inverted statistical logic (requiring $p < 0.05$ on sub-sample splits) and naive friction/capacity heuristics. Superseded by `src/qros/pipeline/evaluation.py`, `src/qros/stats/bootstrap.py`, and `src/qros/pipeline/costs.py`. Must NOT be used for QROS research decisions.
3. **`tests/test_edges.py` $\to$ `ARCHIVE`**
   - *Rationale:* Preserved in historical archive as contract tests for legacy code, but excluded from production research test suites.

---

## 5. Answers to Specific Project Manager Questions

1. **Does the module prove a real edge, or only classify and audit evidence?**  
   *It only classifies user-supplied numbers and executes heuristic audits; it cannot prove the existence of an edge.*
2. **Can the audit be passed with weak, synthetic, or misleading inputs?**  
   *YES. Linearly scaling returns by 0.98 passes curve-fitting; fabricating two PnL numbers passes capacity; splitting a regime-shifted series passes the coincidence test.*
3. **Does $n\_trials$ come from a trustworthy registered ledger, or can the caller game it?**  
   *The caller passes $n\_trials$ directly as an integer argument, allowing complete multiple-testing evasion.*
4. **Is the capacity check economically meaningful at institutional scale?**  
   *NO. It is a simple ratio comparison of two caller-supplied numbers with zero market impact mechanics.*
5. **Does the execution check model real impact, or only a simplistic slippage subtraction?**  
   *Only a simplistic basis point subtraction, ignoring dynamic spread regimes and latency.*
6. **Does the permutation/coincidence logic test true robustness, or only generic half-sample difference?**  
   *It tests half-sample difference and fatally demands $p < 0.05$, which erroneously selects for non-stationary strategies.*
7. **Does the taxonomy create scientific value, or just a vocabulary layer?**  
   *It is purely a vocabulary layer; modern QROS uses quantitative `ValidationProfile` regimes.*
8. **Does any part of the code violate strict QROS research governance?**  
   *YES. The bypassable trial count, inverted coincidence test, and lack of pre-registration integration violate QROS core standards.*
9. **Can this code be safely kept as documentation, or must it be reworked before reuse?**  
   *It should be kept strictly as historical/reference material (`ARCHIVE`). Any future reuse would require a total rewrite.*
10. **What is the correct disposition for each module?**  
    - `src/qros/edges/taxonomy.py`: **`ARCHIVE`**  
    - `src/qros/edges/audit.py`: **`REJECT`**  
    - `tests/test_edges.py`: **`ARCHIVE`**  

---

## 6. Definitive Decision

**Decision:** **DO NOT ADMIT LEGACY EDGE LOGIC INTO ACTIVE QROS PIPELINE.**  
All empirical evaluations must continue using the institutional validation engine (`src/qros/pipeline/evaluation.py`), centralized trial accounting (`GlobalTrialLedger`), class-calibrated validation profiles (`ValidationProfile`), and point-in-time friction models (`TransactionCostModel`).
