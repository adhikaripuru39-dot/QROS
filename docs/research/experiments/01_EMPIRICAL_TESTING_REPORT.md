# QROS Empirical Testing & Hypothesis Validation Report
**Date:** 2026-08-15 02:47:28 UTC  
**Asset:** XAUUSD (Spot Gold)  
**Methodology:** Strict Pre-Registered Backtesting under Realistic Transaction Costs  
**Global Multiple-Testing Accounting:** Cumulative Trials $K = 29$  

---

## 1. Executive Summary of Empirical Findings

| Experiment ID | Hypothesis ID | Timeframe | Research Class | Trades ($N$) | Gross PF | Net PF | Net Sharpe | DSR Score | Bootstrap 95% CI | Conclusion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`QROS-EXP-000001`](../../../experiments/records/QROS-EXP-000001.yaml) | `QROS-HYP-000001` | `M5` | `CLASS-II` | 5 | 1.22 | 1.08 | 0.41 | 0.000 | [-14.24, 9.27] | **`INCONCLUSIVE`** |
| [`QROS-EXP-000002`](../../../experiments/records/QROS-EXP-000002.yaml) | `QROS-HYP-000002` | `H1` | `CLASS-III` | 0 | 1.00 | 1.00 | 0.00 | 0.000 | [0.00, 0.00] | **`INCONCLUSIVE`** |
| [`QROS-EXP-000003`](../../../experiments/records/QROS-EXP-000003.yaml) | `QROS-HYP-000003` | `D1` | `CLASS-IV` | 22 | 1.23 | 1.21 | 1.07 | 0.000 | [-7.12, 7.28] | **`INCONCLUSIVE`** |

---

## 2. Detailed Statistical Validation Results by Hypothesis

### QROS-EXP-000001: London Open Initial Balance Expansion and Intraday Momentum (QROS-HYP-000001)
- **Research Class & Profile:** `CLASS-II` (INTRADAY-MOM_DEFAULT)
- **Data Partitions:** Non-OOS Tier 1 (EDA) & Tier 2 (Train) | Total observations $T = 5,998$ bars (0.08 years)
- **Trade Sample Count:** $N = 5$ trades | Effective sample size $N_{\text{eff}} = 5.0$
- **Transaction Friction Applied:** Nominal Spread = 20.0 pts, Slippage Multiplier = 2.5x, Latency = 200.0ms

#### Core Performance Metrics:
- **Gross Profit Factor:** 1.22
- **Net Profit Factor:** **1.08** (Target: $\ge 1.35$)
- **Net Annualized Sharpe:** **0.41** (Target: $\ge 1.40$)
- **Net Annualized Sortino:** 0.60
- **Deflated Sharpe Ratio (DSR):** **0.000** (Hurdle: $\ge 0.950$, $SR^* = 1.40$, evaluated at $K = 29$)
- **Stationary Block Bootstrap 95% CI:** [-14.236, 9.269] (Strictly Positive: `False`)
- **Higher Moments:** Skewness = 1.02, Excess Kurtosis = 1.77
- **Tail Risk:** 99% Historical VaR = 0.39%, 99% Expected Shortfall (CVaR) = 0.39%

#### Gate Audit Findings & Failure Diagnostics:
- **[FAIL]** Insufficient discrete trades: N=5 < 400
- **[FAIL]** Insufficient effective trades: N_eff=5.0 < 200
- **[FAIL]** Insufficient observations: T=5998 < 15000
- **[FAIL]** Insufficient calendar span: Span=0.1y < 3.0y
- **[FAIL]** Net Profit Factor failed: PF=1.08 < 1.35
- **[FAIL]** Net Sharpe failed: SR=0.41 < 1.40
- **[FAIL]** DSR score failed: DSR=0.000 < 0.950 (K=24)
- **[FAIL]** Bootstrap 95% CI lower bound is non-positive: CI_lower=-14.236 <= 0.0

- **Final Mission Conclusion:** **`INCONCLUSIVE`**

---

### QROS-EXP-000002: Multi-Hour Range Compression Breakout and Volatility Regime Transition (QROS-HYP-000002)
- **Research Class & Profile:** `CLASS-III` (SWING-STATARB_DEFAULT)
- **Data Partitions:** Non-OOS Tier 1 (EDA) & Tier 2 (Train) | Total observations $T = 5,998$ bars (1.02 years)
- **Trade Sample Count:** $N = 0$ trades | Effective sample size $N_{\text{eff}} = 1.0$
- **Transaction Friction Applied:** Nominal Spread = 20.0 pts, Slippage Multiplier = 2.0x, Latency = 0.0ms

#### Core Performance Metrics:
- **Gross Profit Factor:** 1.00
- **Net Profit Factor:** **1.00** (Target: $\ge 1.30$)
- **Net Annualized Sharpe:** **0.00** (Target: $\ge 1.20$)
- **Net Annualized Sortino:** 0.00
- **Deflated Sharpe Ratio (DSR):** **0.000** (Hurdle: $\ge 0.950$, $SR^* = 1.42$, evaluated at $K = 29$)
- **Stationary Block Bootstrap 95% CI:** [0.000, 0.000] (Strictly Positive: `False`)
- **Higher Moments:** Skewness = 0.00, Excess Kurtosis = 0.00
- **Tail Risk:** 99% Historical VaR = 0.00%, 99% Expected Shortfall (CVaR) = 0.00%

#### Gate Audit Findings & Failure Diagnostics:
- **[FAIL]** Insufficient discrete trades: N=1 < 150
- **[FAIL]** Insufficient effective trades: N_eff=1.0 < 80
- **[FAIL]** Insufficient calendar span: Span=1.0y < 5.0y
- **[FAIL]** Net Profit Factor failed: PF=1.00 < 1.30
- **[FAIL]** Net Sharpe failed: SR=0.00 < 1.20
- **[FAIL]** DSR score failed: DSR=0.000 < 0.950 (K=26)
- **[FAIL]** Bootstrap 95% CI lower bound is non-positive: CI_lower=0.000 <= 0.0

- **Final Mission Conclusion:** **`INCONCLUSIVE`**

---

### QROS-EXP-000003: Macro Mean Reversion Following 3-Sigma Daily Return Extensions (QROS-HYP-000003)
- **Research Class & Profile:** `CLASS-IV` (MACRO-REGIME_DEFAULT)
- **Data Partitions:** Non-OOS Tier 1 (EDA) & Tier 2 (Train) | Total observations $T = 1,200$ bars (4.65 years)
- **Trade Sample Count:** $N = 22$ trades | Effective sample size $N_{\text{eff}} = 14.3$
- **Transaction Friction Applied:** Nominal Spread = 20.0 pts, Slippage Multiplier = 1.5x, Latency = 0.0ms

#### Core Performance Metrics:
- **Gross Profit Factor:** 1.23
- **Net Profit Factor:** **1.21** (Target: $\ge 1.50$)
- **Net Annualized Sharpe:** **1.07** (Target: $\ge 1.00$)
- **Net Annualized Sortino:** 1.38
- **Deflated Sharpe Ratio (DSR):** **0.000** (Hurdle: $\ge 0.900$, $SR^* = 1.45$, evaluated at $K = 29$)
- **Stationary Block Bootstrap 95% CI:** [-7.124, 7.283] (Strictly Positive: `False`)
- **Higher Moments:** Skewness = 0.82, Excess Kurtosis = 2.28
- **Tail Risk:** 99% Historical VaR = 7.27%, 99% Expected Shortfall (CVaR) = 7.27%

#### Gate Audit Findings & Failure Diagnostics:
- **[FAIL]** Insufficient discrete trades: N=22 < 40
- **[FAIL]** Insufficient effective trades: N_eff=14.3 < 30
- **[FAIL]** Insufficient observations: T=1200 < 3000
- **[FAIL]** Insufficient calendar span: Span=4.7y < 12.0y
- **[FAIL]** Net Profit Factor failed: PF=1.21 < 1.50
- **[FAIL]** DSR score failed: DSR=0.000 < 0.900 (K=28)
- **[FAIL]** Bootstrap 95% CI lower bound is non-positive: CI_lower=-7.124 <= 0.0

- **Final Mission Conclusion:** **`INCONCLUSIVE`**

---
