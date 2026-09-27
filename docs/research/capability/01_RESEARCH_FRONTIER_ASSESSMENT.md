# QROS Research Frontier & Capability Assessment

**Document ID:** `QROS-CAP-001`  
**Mission:** QROS-RESEARCH-010  
**Asset:** XAUUSD (Spot Gold vs. US Dollar)  
**Date:** 2026-08-15  
**Governing Standard:** QROS-STD-VAL-001 & QROS-STD-STAT-005  
**Current Global Trials:** $K = 119$  

---

## 1. Executive Summary

Across Missions QROS-RESEARCH-001 through 009, QROS constructed institutional statistical validation architecture and executed two empirical hypothesis discovery cycles on XAUUSD. The cumulative empirical result is:
- **6 Pre-Registered Hypotheses Tested:** 3 Classified as `DATA INSUFFICIENT`, 3 Classified as `REJECTED`.
- **0 Edge Candidates Promoted.**
- **Multiple-Testing Accounting:** Monotonically tracked at $K = 119$.

This assessment rigorously analyzes the mathematical and structural root causes of these results and formally answers the 8 primary research capability questions.

---

## 2. Answers to the 8 Primary Research Capability Questions

### Question 1: What market phenomena can still be meaningfully researched using the currently available XAUUSD datasets?
- **Macro Multi-Month Trend Regimes (D1):** The 14.0-year continuous D1 dataset (3,600 non-OOS daily bars, 2009–2023) provides sufficient sample size ($T \ge 3,000$) to evaluate multi-month monetary cycle regimes, long-term volatility clustering, and fat-tailed distribution properties.
- **Univariate Daily Technical Formations (D1):** Long-term moving average crosses (50/200 MA), 52-week breakout persistence, and multi-year cyclical seasonalities (e.g. Q1 jewelry fabrication demand / Indian wedding season vs Q3 summer doldrums).
- **Short-Term Exploratory Volatility Diagnostics (H1 / M5):** Basic intraday diurnal spread profiling and exploratory session volume dispersion within the narrow available window.

---

### Question 2: What phenomena CANNOT be researched with current data?
1. **Intraday Session & Momentum Dynamics (Class II):** Blocked by MT5 broker feed capping history to 10,000 bars ($41.6$ days on M5). Impossible to satisfy Class II power hurdles ($N \ge 400$, $\text{Span} \ge 3.0\text{y}$).
2. **Multi-Hour Volatility Compression & Breakout (Class III):** Blocked on H1 ($1.36$ years / 8,000 bars) because rare structural compression states yield insufficient event frequency ($N < 150$).
3. **Cross-Timeframe Higher-Order Conditioning (Class III / IV):** Blocked by **timestamp disjointness**. The D1 non-OOS partition spans 2009–2023, while the H1 non-OOS partition spans 2024–2026. Merging D1 macro indicators onto H1 bars produces 100% NaN indicators.
4. **Order Flow Imbalance & Microstructure Liquidity (Class I / II):** Blocked by lack of Level-2/Level-3 limit order book depth, tick-by-tick bid/ask quotes, and volume-at-price execution delta.
5. **Macro Fundamental & Intermarket Arbitrage (Class IV / V):** Blocked by absence of auxiliary macro time-series (US 10-Year Real Yields / TIPS, US Dollar Index DXY, Silver/Gold Ratio XAGUSD, COMEX Futures Term Structure).

---

### Question 3: Which research classes are currently viable?
- **CLASS-IV (Macro & Structural Regime):** **CONDITIONALLY VIABLE on D1 only**. Requires hypotheses that generate $\ge 40$ trades over 12+ years and hold positions for weeks to months to overcome wide confidence intervals and transaction costs.

---

### Question 4: Which research classes are effectively blocked?
- **CLASS-I (High-Frequency & Microstructure):** **COMPLETELY BLOCKED**. (Requires tick-level L2/L3 order book data and sub-millisecond timestamp resolution).
- **CLASS-II (Intraday Session & Momentum):** **COMPLETELY BLOCKED**. (Requires $\ge 3.0$ years of continuous M1/M5 data; currently only 41.6 days available).
- **CLASS-III (Swing & Multi-Day Stat-Arb):** **BLOCKED / HIGH RISK**. (Requires $\ge 5.0$ years of continuous H1 data and cross-timeframe alignment; currently only 1.36 years available).
- **CLASS-V (Cross-Asset & Macro Factor):** **COMPLETELY BLOCKED**. (Requires synchronized multi-asset panel data).

---

### Question 5: Which additional data would provide the greatest increase in research capability?
1. **Multi-Year Institutional Tick / M1 Historical Archive for XAUUSD (10–15 Years):**
   - Instantly unblocks Class II (Intraday Momentum, London/NY Breakouts, Session Reversals) and Class III (Multi-Day Swings).
   - Enables exact simulation of bid-ask spread variation, diurnal liquidity drops, and high-frequency trade execution without broker-imposed 10,000-bar pagination truncations.
2. **Synchronized Macro Intermarket Datasets (Daily/Hourly, 15+ Years):**
   - US 10-Year Real Yields (FRED: `DFII10`), US 10-Year Nominal (`DGS10`), US Dollar Index (`DXY` / `DTWEXBGS`), Silver (`XAGUSD`), COMEX Gold Futures (`GC` active & term structure), and CFTC Commitments of Traders (COT).
   - Unblocks Class IV and Class V fundamental monetary and relative value research.

---

### Question 6: Should QROS expand beyond XAUUSD-only?
**YES, UNEQUIVOCALLY.**
Gold is not an isolated speculative instrument. Economically, spot gold ($P_{\text{gold}}$) is a non-yielding monetary reserve asset governed by:
$$P_{\text{gold}} \propto f(\text{Real US Interest Rates}, \text{USD Purchasing Power}, \text{Central Bank Reserves}, \text{Inflation Expectations}, \text{Geopolitical Risk Premium})$$
Attempting to predict gold returns using purely univariate price patterns (lagged closes and moving averages) ignores 90% of the institutional price discovery mechanism.

---

### Question 7: Which data source provides the highest research value per unit of acquisition complexity and cost?
1. **FRED (Federal Reserve Bank of St. Louis API):** Cost: **FREE**, Complexity: **LOW**. Provides 50+ years of daily US 10Y real yields, TIPS, breakeven inflation, federal funds rate, and trade-weighted dollar indices.
2. **Dukascopy Historical Tick & M1 Public Repository:** Cost: **FREE / OPEN**, Complexity: **LOW-MEDIUM**. Provides 15+ years of continuous, bid/ask tick and M1 data for XAUUSD, XAGUSD, EURUSD, USDJPY, and major indices.
3. **CFTC Socrata Public Data Portal:** Cost: **FREE**, Complexity: **LOW**. Provides weekly institutional commercial vs non-commercial positioning back to 2000.

---

### Question 8: Which research domains have NOT yet been adequately explored?
1. **Real Yield & Macro Regime Decoupling:** Gold price momentum conditioned on US 10Y Real Yield divergence.
2. **Currency Denominator & Cross-Currency Gold Arbitrage:** Gold priced in EUR, JPY, and CHF vs XAUUSD to isolate pure monetary debasement from USD fluctuations.
3. **Gold/Silver Ratio (XAU/XAG) Mean-Reversion & Relative Value:** Cointegration and spread mean reversion between precious metals.
4. **Institutional CFTC Commercial Hedger Extremes:** COT Net Speculator positioning extremes predicting multi-month trend exhaustion.
5. **Physical LBMA Fixing & Diurnal Spread Dislocation:** London 10:30 & 15:00 UTC Gold Fixing flow dynamics using tick-level bid/ask spreads.

---

## 3. Methodological Summary

Current univariate MT5 historical data has reached its scientific frontier. Attempting further parameter iterations on existing truncated datasets violates QROS governance and risks manufacturing curve-fitted false positives. Research must expand into **high-depth historical archives** and **macro intermarket series**.
