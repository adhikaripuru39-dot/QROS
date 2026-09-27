# QROS Historical Coverage Report: XAUUSD Expanded Datasets (v2.0.0)
**Report Identifier:** QROS-REP-DATA-002  
**Mission:** QROS-DATA-EXPANSION-001  
**Primary Asset:** XAUUSD (Spot Gold vs. US Dollar)  
**Ingestion Source:** MetaTrader 5 Institutional Broker Feed (`MetaQuotes Ltd.`)  
**Status:** Approved Canonical Baseline  

---

## 1. Executive Summary

This report documents the empirical historical depth, temporal coverage, and observational resolution achieved across all active versions (`v1.0.0` and `v2.0.0`) of the primary research asset (**XAUUSD**).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    XAUUSD EXPANDED COVERAGE SPECTRUM (v2.0.0)               │
├───────────┬──────────────┬───────────────────────────────┬──────────────────┤
│ Timeframe │ Total Bars   │ Calendar Date Range           │ Total Span       │
├───────────┼──────────────┼───────────────────────────────┼──────────────────┤
│ M1        │ 9,999 Bars   │ 2026-08-05 10:21 -> 2026-08-14│ 9.5 Days         │
│ M5        │ 9,999 Bars   │ 2026-06-23 22:50 -> 2026-08-14│ 52.0 Days        │
│ H1        │ 9,999 Bars   │ 2024-11-27 13:00 -> 2026-08-14│ 1.71 Years       │
│ D1        │ 2,000 Bars   │ 2018-11-14 00:00 -> 2026-08-14│ 7.75 Years       │
└───────────┴──────────────┴───────────────────────────────┴──────────────────┘
```

---

## 2. Granular Timeframe Coverage Analysis

### A. High-Frequency Microstructure Tier (`M1`)
- **Dataset ID:** `QROS-DATA-XAUUSD-M1-v2.0.0`
- **Total Ingested Observations:** $9,999$ 1-minute bars.
- **Calendar Horizon:** August 5, 2026 $\to$ August 14, 2026 ($0.026$ years / $9.5$ trading days).
- **Research Utility:** Microstructural order flow dynamics, sub-hour liquidity shocks, spread expansion during high-impact macroeconomic releases (e.g. CPI, Non-Farm Payrolls, FOMC rate announcements), and Class I / High-Frequency validation.

### B. Intraday Momentum Tier (`M5`)
- **Dataset ID:** `QROS-DATA-XAUUSD-M5-v2.0.0`
- **Total Ingested Observations:** $9,999$ 5-minute bars (doubled from $5,000$ in `v1.0.0`).
- **Calendar Horizon:** June 23, 2026 $\to$ August 14, 2026 ($0.142$ years / $52.0$ trading days).
- **Research Utility:** Session breakout models (London Open, New York Open), intraday mean reversion, and Class II Intraday Momentum validation.

### C. Swing & Statistical Arbitrage Tier (`H1`)
- **Dataset ID:** `QROS-DATA-XAUUSD-H1-v2.0.0`
- **Total Ingested Observations:** $9,999$ 1-hour bars (doubled from $5,000$ in `v1.0.0`).
- **Calendar Horizon:** November 27, 2024 $\to$ August 14, 2026 ($1.714$ years / $625.4$ trading days).
- **Research Utility:** Multi-day swing holding periods ($4 \to 72$ hours), volatility regime shifts, and Class III Swing / Stat-Arb validation.

### D. Macro & Daily Regime Tier (`D1`)
- **Dataset ID:** `QROS-DATA-XAUUSD-D1-v2.0.0`
- **Total Ingested Observations:** $2,000$ daily bars.
- **Calendar Horizon:** November 14, 2018 $\to$ August 14, 2026 ($7.748$ years / $2,830$ calendar days).
- **Research Utility:** Multi-year structural trend following, real interest rate cycles, central bank reserve accumulation trends, and Class IV Macro Regime validation.

---

## 3. Version Comparison (`v1.0.0` vs. `v2.0.0`)

| Metric | Version v1.0.0 | Version v2.0.0 | Delta / Expansion Factor |
| :--- | :--- | :--- | :--- |
| **M1 Resolution** | Not Ingested ($0$) | $9,999$ Bars | **+9,999 Bars** (New Micro Tier) |
| **M5 Resolution** | $5,000$ Bars | $9,999$ Bars | **+99.98%** ($\sim 2\times$ Increase) |
| **H1 Resolution** | $5,000$ Bars | $9,999$ Bars | **+99.98%** ($\sim 2\times$ Increase) |
| **D1 Resolution** | $2,000$ Bars | $2,000$ Bars | **$1.0\times$** (Full Broker Depth) |
| **Total Database Observations** | $12,000$ Bars | $31,997$ Bars | **$+166.6\%$** Overall Growth |
