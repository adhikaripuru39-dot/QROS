# QROS Transaction Cost & Friction Impact Report: Cycle II
**Date:** 2026-08-15 04:51:24 UTC  
**Asset:** XAUUSD  
**Cost Engine:** `TransactionCostModel`  

---

## 1. Friction Drag Analysis per Hypothesis

| Experiment ID | Hypothesis ID | Class | Nominal Spread | Slippage Stress | Mean Holding | Gross Return | Net Return | Friction Drag | Cost Resilience |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `QROS-EXP-000007` | `QROS-HYP-000004` | `CLASS-IV` | 20 pts | 1.5x | 11.7 bars | 0.65% | 0.62% | 0.030% (4.7%) | **HIGH (Resilient)** |
| `QROS-EXP-000008` | `QROS-HYP-000005` | `CLASS-IV` | 20 pts | 1.5x | 4.5 bars | 0.00% | -0.03% | 0.030% (1486.9%) | **VULNERABLE** |
| `QROS-EXP-000009` | `QROS-HYP-000006` | `CLASS-III` | 20 pts | 2.0x | 0.0 bars | 0.00% | 0.00% | 0.000% (100.0%) | **MODERATE** |