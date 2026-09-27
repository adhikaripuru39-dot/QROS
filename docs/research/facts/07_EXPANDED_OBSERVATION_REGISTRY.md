# QROS Expanded Market Observation Registry: XAUUSD
**Last Updated:** 2026-08-15 04:42:10 UTC  
**Asset:** XAUUSD  
**Total Cataloged Observations:** 18  

---

| Obs ID | Domain Name | Timeframe | Sample $N$ | Metric | Value | Viable Candidate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `QROS-OBS-001` | Return Distributions & Fat Tails | `D1` | 3,599 | Excess Kurtosis & Student-t df | 5.1594 | **YES** |
| `QROS-OBS-002` | Volatility Clustering | `H1` | 7,999 | Lag-1 Absolute Return Autocorrelation | 0.3121 | **YES** |
| `QROS-OBS-003` | Volatility Regimes | `H1` | 7,977 | Garman-Klass Volatility Persistence Ratio | 0.8105 | **YES** |
| `QROS-OBS-004` | Autocorrelation & Serial Independence | `M5` | 7,999 | Lag-1 Linear Return Autocorrelation | -0.0119 | NO |
| `QROS-OBS-005` | Momentum & Directional Runs | `H1` | 4,068 | Mean Directional Run Length | 1.9661 | NO |
| `QROS-OBS-006` | Mean Reversion & Spread Decay | `H1` | 7,953 | 48-Bar Moving Average Deviation Half-Life | 23.4164 | **YES** |
| `QROS-OBS-007` | Range Expansion & Contraction | `H1` | 7,976 | ATR Fast/Slow Ratio Compression Events | 278.0000 | **YES** |
| `QROS-OBS-008` | Compression -> Expansion Dynamics | `D1` | 3,594 | NR7 Frequency Count | 534.0000 | **YES** |
| `QROS-OBS-009` | Intraday Session Volatility Breakdown | `M5` | 8,000 | London/NY Overlap vs. Asian Range Ratio | 0.9097 | **YES** |
| `QROS-OBS-010` | London Open Liquidity & Volume Surge | `M5` | 8,000 | London Open Volume Expansion Multiplier | 0.6657 | **YES** |
| `QROS-OBS-011` | Previous-Day High / Low Interaction | `H1` | 351 | PDH / PDL Test Frequency | 0.6800 | **YES** |
| `QROS-OBS-012` | Initial Balance Structure | `M5` | 500 | Initial Balance Extension Probability | 0.7400 | **YES** |
| `QROS-OBS-013` | Trend / Range Regimes & Variance Ratio | `D1` | 3,599 | 5-Day Lo-MacKinlay Variance Ratio | 0.9855 | **YES** |
| `QROS-OBS-014` | Extreme Returns & Tail Asymmetry | `D1` | 3,599 | 1st Percentile vs 99th Percentile Tail Ratio | 1.0853 | **YES** |
| `QROS-OBS-015` | Conditional Return Distributions | `H1` | 1,000 | High Volatility Return Kurtosis Ratio | 2.4500 | **YES** |
| `QROS-OBS-016` | Time-of-Day Diurnal Seasonality | `M5` | 8,000 | Daily Settlement Roll Spread Expansion Multiplier | 1.1046 | **YES** |
| `QROS-OBS-017` | Liquidity & Spread Proxies | `M5` | 7,999 | Normalized Amihud Illiquidity Score (x10^6) | 0.3773 | NO |
| `QROS-OBS-018` | Cross-Timeframe Volatility Modulation | `H1 -> M5` | 1,000 | H1 Volatility Trend Modulation Correlation | 0.5800 | **YES** |