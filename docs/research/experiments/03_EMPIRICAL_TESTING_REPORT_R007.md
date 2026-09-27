# QROS Empirical Testing & Hypothesis Validation Report (R007)
**Date:** 2026-08-15 04:33:54 UTC  
**Asset:** XAUUSD (Spot Gold)  
**Operating Dataset:** `QROS-DATA-XAUUSD-v3.0.0` (Non-OOS Partitions: Tiers 1-3)  
**Methodology:** Strict Point-in-Time Pre-Registered Empirical Evaluation under Friction Stress  
**Global Multiple-Testing Accounting:** Cumulative Trials $K = 35$  

---

## 1. Executive Summary of Empirical Findings

| Experiment ID | Hypothesis ID | Timeframe | Research Class | Trades ($N$) | Gross PF | Net PF | Net Sharpe | DSR Score | Bootstrap 95% CI | Standardized Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`QROS-EXP-000004`](../../../experiments/records/QROS-EXP-000004.yaml) | `QROS-HYP-000001` | `M5` | `CLASS-II` | 7 | 1.61 | 1.45 | 2.24 | 1.000 | [-6.87, 8.12] | **`DATA INSUFFICIENT`** |
| [`QROS-EXP-000005`](../../../experiments/records/QROS-EXP-000005.yaml) | `QROS-HYP-000002` | `H1` | `CLASS-III` | 0 | 1.00 | 1.00 | 0.00 | 0.000 | [0.00, 0.00] | **`DATA INSUFFICIENT`** |
| [`QROS-EXP-000006`](../../../experiments/records/QROS-EXP-000006.yaml) | `QROS-HYP-000003` | `D1` | `CLASS-IV` | 65 | 0.65 | 0.63 | -2.88 | 0.000 | [-8.59, 1.49] | **`REJECTED`** |

---

## 2. Detailed Statistical Validation Results by Hypothesis

### QROS-EXP-000004: London Open Initial Balance Expansion and Intraday Momentum (QROS-HYP-000001)
- **Research Class & Profile:** `CLASS-II` (INTRADAY-MOM_DEFAULT)
- **Data Partitions:** Non-OOS Tiers 1-3 | Total observations $T = 8,000$ bars (0.12 years)
- **Trade Sample Count:** $N = 7$ trades | Effective sample size $N_{\text{eff}} = 7.0$ (Target: $\ge 400$)
- **Transaction Friction Applied:** Nominal Spread = 20.0 pts, Slippage Multiplier = 2.5x, Latency = 200.0ms

#### Core Performance Metrics:
- **Gross Profit Factor:** 1.61
- **Net Profit Factor:** **1.45** (Target: $\ge 1.35$)
- **Net Annualized Sharpe:** **2.24** (Target: $\ge 1.40$)
- **Net Annualized Sortino:** 3.55
- **Deflated Sharpe Ratio (DSR):** **1.000** (Hurdle: $\ge 0.950$, $SR^* = 1.47$, evaluated at $K = 35$)
- **Stationary Block Bootstrap 95% CI:** [-6.868, 8.123] (Strictly Positive: `False`)
- **Higher Moments:** Skewness = 0.69, Excess Kurtosis = -1.16
- **Tail Risk:** 99% Historical VaR = 0.39%, 99% Expected Shortfall (CVaR) = 0.39%

#### Gate Audit Findings & Failure Diagnostics:
- **[FAIL]** Insufficient discrete trades: N=7 < 400
- **[FAIL]** Insufficient effective trades: N_eff=7.0 < 200
- **[FAIL]** Insufficient observations: T=8000 < 15000
- **[FAIL]** Insufficient calendar span: Span=0.1y < 3.0y
- **[FAIL]** Bootstrap 95% CI lower bound is non-positive: CI_lower=-6.868 <= 0.0

- **Standardized Outcome:** **`DATA INSUFFICIENT`**

---

### QROS-EXP-000005: Multi-Hour Range Compression Breakout and Volatility Regime Transition (QROS-HYP-000002)
- **Research Class & Profile:** `CLASS-III` (SWING-STATARB_DEFAULT)
- **Data Partitions:** Non-OOS Tiers 1-3 | Total observations $T = 8,000$ bars (1.36 years)
- **Trade Sample Count:** $N = 0$ trades | Effective sample size $N_{\text{eff}} = 1.0$ (Target: $\ge 150$)
- **Transaction Friction Applied:** Nominal Spread = 20.0 pts, Slippage Multiplier = 2.0x, Latency = 0.0ms

#### Core Performance Metrics:
- **Gross Profit Factor:** 1.00
- **Net Profit Factor:** **1.00** (Target: $\ge 1.30$)
- **Net Annualized Sharpe:** **0.00** (Target: $\ge 1.20$)
- **Net Annualized Sortino:** 0.00
- **Deflated Sharpe Ratio (DSR):** **0.000** (Hurdle: $\ge 0.950$, $SR^* = 1.48$, evaluated at $K = 35$)
- **Stationary Block Bootstrap 95% CI:** [0.000, 0.000] (Strictly Positive: `False`)
- **Higher Moments:** Skewness = 0.00, Excess Kurtosis = 0.00
- **Tail Risk:** 99% Historical VaR = 0.00%, 99% Expected Shortfall (CVaR) = 0.00%

#### Gate Audit Findings & Failure Diagnostics:
- **[FAIL]** Insufficient discrete trades: N=1 < 150
- **[FAIL]** Insufficient effective trades: N_eff=1.0 < 80
- **[FAIL]** Insufficient calendar span: Span=1.4y < 5.0y
- **[FAIL]** Net Profit Factor failed: PF=1.00 < 1.30
- **[FAIL]** Net Sharpe failed: SR=0.00 < 1.20
- **[FAIL]** DSR score failed: DSR=0.000 < 0.950 (K=32)
- **[FAIL]** Bootstrap 95% CI lower bound is non-positive: CI_lower=0.000 <= 0.0

- **Standardized Outcome:** **`DATA INSUFFICIENT`**

---

### QROS-EXP-000006: Macro Mean Reversion Following 3-Sigma Daily Return Extensions (QROS-HYP-000003)
- **Research Class & Profile:** `CLASS-IV` (MACRO-REGIME_DEFAULT)
- **Data Partitions:** Non-OOS Tiers 1-3 | Total observations $T = 3,600$ bars (13.97 years)
- **Trade Sample Count:** $N = 65$ trades | Effective sample size $N_{\text{eff}} = 41.2$ (Target: $\ge 40$)
- **Transaction Friction Applied:** Nominal Spread = 20.0 pts, Slippage Multiplier = 1.5x, Latency = 0.0ms

#### Core Performance Metrics:
- **Gross Profit Factor:** 0.65
- **Net Profit Factor:** **0.63** (Target: $\ge 1.50$)
- **Net Annualized Sharpe:** **-2.88** (Target: $\ge 1.00$)
- **Net Annualized Sortino:** -3.06
- **Deflated Sharpe Ratio (DSR):** **0.000** (Hurdle: $\ge 0.900$, $SR^* = 1.50$, evaluated at $K = 35$)
- **Stationary Block Bootstrap 95% CI:** [-8.592, 1.490] (Strictly Positive: `False`)
- **Higher Moments:** Skewness = 0.82, Excess Kurtosis = 2.14
- **Tail Risk:** 99% Historical VaR = 7.27%, 99% Expected Shortfall (CVaR) = 7.27%

#### Gate Audit Findings & Failure Diagnostics:
- **[FAIL]** Net Profit Factor failed: PF=0.63 < 1.50
- **[FAIL]** Net Sharpe failed: SR=-2.88 < 1.00
- **[FAIL]** DSR score failed: DSR=0.000 < 0.900 (K=34)
- **[FAIL]** Bootstrap 95% CI lower bound is non-positive: CI_lower=-8.592 <= 0.0

- **Standardized Outcome:** **`REJECTED`**

---
