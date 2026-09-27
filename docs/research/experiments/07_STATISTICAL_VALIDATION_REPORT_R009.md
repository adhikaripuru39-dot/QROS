# QROS Statistical Validation & Quality Gate Audit: Cycle II
**Date:** 2026-08-15 04:51:24 UTC  
**Standard:** QROS-STD-VAL-001 Validation Profile Architecture  

---

## 1. Gate-by-Gate Evaluation Audit

| Gate Name | Hurdle Description | QROS-HYP-000004 | QROS-HYP-000005 | QROS-HYP-000006 |
| :--- | :--- | :--- | :--- | :--- |
| **Sample Power ($N \ge N_{\min}$)** | Class min trades & history | **PASS** ($N=52 \ge 30$) | **PASS** ($N=358 \ge 30$) | **FAIL** ($N=0 / 150$) |
| **Net Profit Factor** | PF Net $\ge \text{PF}_{\min}$ | **PASS** (1.59) | **FAIL** (0.96) | **FAIL** (1.00) |
| **Net Annualized Sharpe** | $\text{SR}_{\text{net}} \ge \text{SR}_{\min}$ | **PASS** (3.00) | **FAIL** (-0.23) | **FAIL** (0.00) |
| **Deflated Sharpe Ratio** | $\text{DSR} \ge \text{DSR}_{\min}$ at $K=119$ | **PASS** (1.0000) | **FAIL** (0.0000) | **FAIL** (0.0000) |
| **Bootstrap 95% CI** | CI lower bound $> 0.0$ | **FAIL** (-0.1097) | **FAIL** (-1.9222) | **FAIL** (0.0000) |
| **Overall Gate Outcome** | All hurdles satisfied | **`REJECTED`** | **`REJECTED`** | **`DATA INSUFFICIENT`** |