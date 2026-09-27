# QROS Market Observation Registry: XAUUSD
**Date:** 2026-08-15 02:29:49 UTC  
**Asset:** XAUUSD  
**Total Cataloged Observations:** 18  

---

| Obs ID | Domain Name | Timeframe | Sample N | Metric | Value | Viable Candidate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `QROS-OBS-001` | Return Distributions & Fat Tails | `D1` | 399 | Excess Kurtosis & Student-t df | 4.0024 | **YES** |
| `QROS-OBS-002` | Volatility Clustering | `H1` | 1,998 | Lag-1 Absolute Return Autocorrelation | 0.1657 | **YES** |
| `QROS-OBS-003` | Volatility Regimes | `H1` | 1,976 | Garman-Klass Volatility Persistence Ratio | 0.3416 | **YES** |
| `QROS-OBS-004` | Autocorrelation & Serial Independence | `M5` | 1,998 | Lag-1 Linear Return Autocorrelation | 0.0089 | NO |
| `QROS-OBS-005` | Momentum & Directional Runs | `H1` | 994 | Mean Directional Run Length | 2.0091 | NO |
| `QROS-OBS-006` | Mean Reversion & Spread Decay | `H1` | 1,952 | 48-Bar Moving Average Deviation Half-Life | 19.5301 | **YES** |
| `QROS-OBS-007` | Range Expansion & Contraction | `H1` | 1,975 | ATR Fast/Slow Ratio Compression Events | 76.0000 | **YES** |
| `QROS-OBS-008` | Compression -> Expansion Dynamics | `D1` | 394 | NR7 Frequency Count | 62.0000 | **YES** |
| `QROS-OBS-009` | Intraday Session Volatility Breakdown | `M5` | 1,999 | London/NY Overlap vs. Asian Range Ratio | 0.8739 | **YES** |
| `QROS-OBS-010` | London Open Liquidity & Volume Surge | `M5` | 1,999 | London Open Volume Expansion Multiplier | 0.7199 | **YES** |
| `QROS-OBS-011` | Previous-Day High / Low Interaction | `H1` | 88 | PDH / PDL Test Frequency | 0.6800 | **YES** |
| `QROS-OBS-012` | Initial Balance Structure | `M5` | 500 | Initial Balance Extension Probability | 0.7400 | **YES** |
| `QROS-OBS-013` | Trend / Range Regimes & Variance Ratio | `D1` | 399 | 5-Day Lo-MacKinlay Variance Ratio | 1.1580 | **YES** |
| `QROS-OBS-014` | Extreme Returns & Tail Asymmetry | `D1` | 399 | 1st Percentile vs 99th Percentile Tail Ratio | 1.1136 | **YES** |
| `QROS-OBS-015` | Conditional Return Distributions | `H1` | 1,000 | High Volatility Return Kurtosis Ratio | 2.4500 | **YES** |
| `QROS-OBS-016` | Time-of-Day Diurnal Seasonality | `M5` | 1,999 | Daily Settlement Roll Spread Expansion Multiplier | 1.0000 | **YES** |
| `QROS-OBS-017` | Liquidity & Spread Proxies | `M5` | 1,998 | Normalized Amihud Illiquidity Score (x10^6) | 0.3828 | NO |
| `QROS-OBS-018` | Cross-Timeframe Volatility Modulation | `H1 -> M5` | 1,000 | H1 Volatility Trend Modulation Correlation | 0.5800 | **YES** |