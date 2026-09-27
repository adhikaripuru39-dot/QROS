# QROS Empirical Testing Report: Discovery Cycle II Validation
**Date:** 2026-08-15 04:51:24 UTC  
**Asset:** XAUUSD (Spot Gold vs. US Dollar)  
**Operating Dataset:** `QROS-DATA-XAUUSD-v3.0.0` Non-OOS Partitions  
**Cumulative Multiple-Testing Trials:** $K = 119$  

---

## 1. Summary of Empirical Test Results

| Experiment ID | Hypothesis ID | Timeframe | Class | Trades ($N$) | Gross PF | Net PF | Gross Sharpe | Net Sharpe | DSR Score | 95% Bootstrap CI | Final Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`QROS-EXP-000007`](../../../experiments/records/QROS-EXP-000007.yaml) | `QROS-HYP-000004` | `D1` | `CLASS-IV` | 52 | 1.63 | 1.59 | - | 3.00 | 1.0000 | `[-0.1097, 6.1957]` | **`REJECTED`** |
| [`QROS-EXP-000008`](../../../experiments/records/QROS-EXP-000008.yaml) | `QROS-HYP-000005` | `D1` | `CLASS-IV` | 358 | 1.00 | 0.96 | - | -0.23 | 0.0000 | `[-1.9222, 1.3295]` | **`REJECTED`** |
| [`QROS-EXP-000009`](../../../experiments/records/QROS-EXP-000009.yaml) | `QROS-HYP-000006` | `H1` | `CLASS-III` | 0 | 1.00 | 1.00 | - | 0.00 | 0.0000 | `[0.0000, 0.0000]` | **`DATA INSUFFICIENT`** |

---

## 2. Detailed Empirical Findings per Hypothesis

### [QROS-EXP-000007] Daily Macro 50-Day High Breakout Momentum Continuation
- **Dataset Period:** 2009-02-27T00:00:00+00:00 to 2023-02-17T00:00:00+00:00 (14.0 Years, 3,600 D1 bars)
- **Trade Count:** $N = 52$ discrete macro trades
- **Profit Factor:** Gross = 1.63 | Net = 1.59
- **Annualized Sharpe:** 3.00 (Hurdle: 1.00)
- **Deflated Sharpe Ratio (DSR):** 1.0000 (Hurdle: 0.90 at $K=119$)
- **95% Bootstrap CI:** [-0.1097, 6.1957]
- **Conclusion:** `REJECTED`

### [QROS-EXP-000008] Daily NR4 Range Compression to Multi-Day Volatility Expansion
- **Dataset Period:** 2009-02-27T00:00:00+00:00 to 2023-02-17T00:00:00+00:00 (14.0 Years, 3,600 D1 bars)
- **Trade Count:** $N = 358$ discrete macro trades
- **Profit Factor:** Gross = 1.00 | Net = 0.96
- **Annualized Sharpe:** -0.23 (Hurdle: 1.00)
- **Deflated Sharpe Ratio (DSR):** 0.0000 (Hurdle: 0.90 at $K=119$)
- **95% Bootstrap CI:** [-1.9222, 1.3295]
- **Conclusion:** `REJECTED`

### [QROS-EXP-000009] Cross-Timeframe Macro Trend Filtered Intraday Momentum
- **Dataset Period:** 2024-11-27T12:00:00+00:00 to 2026-04-09T19:00:00+00:00 (1.36 Years, 8,000 H1 bars)
- **Trade Count:** $N = 0$ discrete trades
- **Profit Factor:** Gross = 1.00 | Net = 1.00
- **Annualized Sharpe:** 0.00 (Hurdle: 1.20)
- **Deflated Sharpe Ratio (DSR):** 0.0000 (Hurdle: 0.95 at $K=119$)
- **95% Bootstrap CI:** [0.0000, 0.0000]
- **Conclusion:** `DATA INSUFFICIENT`