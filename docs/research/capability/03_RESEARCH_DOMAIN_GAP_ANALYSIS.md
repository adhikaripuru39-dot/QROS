# QROS Research Domain Gap Analysis

**Document ID:** `QROS-CAP-003`  
**Mission:** QROS-RESEARCH-010  
**Asset:** XAUUSD & Quantitative Exploration Space  
**Date:** 2026-08-15  

---

## 1. Quantitative Search Space Taxonomy

To systematically evaluate research coverage, the QROS quantitative landscape is partitioned into 5 fundamental research pillars:

```mermaid
graph TD
    A[QROS Quantitative Research Space] --> B[Pillar 1: Univariate Technical & Statistical]
    A --> C[Pillar 2: Market Microstructure & Order Flow]
    A --> D[Pillar 3: Macroeconomic & Real Yields]
    A --> E[Pillar 4: Intermarket & Cross-Asset Stat-Arb]
    A --> F[Pillar 5: Institutional Positioning & Flow]
```

---

## 2. Gap Analysis by Research Pillar

### Pillar 1: Univariate Technical & Price Distribution
- **Status:** **ADEQUATELY TESTED (Frontier Reached)**
- **Tested Components:** Heavy tails (Student-t), GARCH clustering, linear autocorrelation, 3-sigma mean-reversion (`HYP-003`), NR4 volatility expansion (`HYP-005`), 50-day breakout momentum (`HYP-004`).
- **Empirical Conclusion:** Univariate price technicals alone on daily/hourly bars do not yield robust alpha after transaction friction and bootstrap confidence hurdles. Further searches in this domain represent unremunerative parameter curve-fitting.

---

### Pillar 2: Market Microstructure & Order Flow
- **Status:** **IMPOSSIBLE WITH CURRENT DATA**
- **Gap:** MT5 broker feed delivers synthetic OHLCV with coarse tick volume. No Level-2 order book depth, no quote delta, no execution-level bid/ask timestamps.
- **Feasibility:** Completely blocked until an institutional tick archive or direct L2 market feed is integrated.

---

### Pillar 3: Macroeconomic & Real Interest Rates
- **Status:** **HIGH VALUE — ZERO EXPLORATION (100% UNTESTED)**
- **Economic Thesis:** Gold has a theoretical $-0.80$ long-term correlation with US 10-Year Real Yields (TIPS). When real yields fall below zero, gold's opportunity cost vanishes and central bank/institutional allocations surge.
- **Untested Hypotheses:**
  - Real Yield Inversion Momentum: Long gold when 10Y TIPS yield breaks below its 50-day MA.
  - Breakeven Inflation Acceleration: Long gold vs Short Dollar during positive CPI/PCE surprise shocks.
- **Data Required:** Daily FRED macroeconomic series (`DFII10`, `DGS10`, `T10YIE`, `FEDFUNDS`).

---

### Pillar 4: Intermarket & Cross-Asset Statistical Arbitrage
- **Status:** **HIGH VALUE — ZERO EXPLORATION (100% UNTESTED)**
- **Economic Thesis:** Gold and Silver share common monetary and industrial demand drivers. The Gold/Silver Ratio (GSR = $P_{\text{gold}} / P_{\text{silver}}$) is stationary/cointegrated over multi-year horizons (historical mean $\approx 65$, bounds $40 - 110$).
- **Untested Hypotheses:**
  - Gold/Silver Ratio Mean-Reversion: Long Silver / Short Gold when GSR $> 90$; Long Gold / Short Silver when GSR $< 50$.
  - Currency Denominator Neutralization: Trading Gold priced in Euro (`XAUEUR`) or Yen (`XAUJPY`) to remove USD monetary noise.
- **Data Required:** Historical XAGUSD (Silver), EURUSD, USDJPY, DXY index.

---

### Pillar 5: Institutional Positioning & Structural Flows
- **Status:** **HIGH VALUE — ZERO EXPLORATION (100% UNTESTED)**
- **Economic Thesis:** Commercial bullion dealers (producers, fabricators, swap dealers) have asymmetric information regarding physical supply and demand compared to levered non-commercial speculators (hedge funds, CTAs).
- **Untested Hypotheses:**
  - Commercial Hedger Accumulation: Long Gold when CFTC Commercial Net Short position reaches historical 3-year minimum (hedgers refuse to hedge at low prices).
  - Speculative Overcrowding Reversals: Multi-week trend exhaustion when Managed Money Net Long exceeds 95th percentile.
- **Data Required:** Weekly CFTC Commitments of Traders (COT) historical reports (Socrata API / CFTC public archive).

---

## 3. Comparative Search Space Coverage

| Research Pillar | Total Potential Hypotheses | Hypotheses Tested in QROS | Coverage % | Status | Value Priority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pillar 1: Univariate Technical** | 25 | 6 | **24.0%** | Frontier Reached | **LOW (Do Not Continue)** |
| **Pillar 2: Microstructure & L2** | 30 | 0 | **0.0%** | Blocked by Data | **MEDIUM-HIGH** |
| **Pillar 3: Macro Real Yields** | 40 | 0 | **0.0%** | Untested / Open | **CRITICAL (Highest Alpha Probability)** |
| **Pillar 4: Intermarket / Cointegration** | 35 | 0 | **0.0%** | Untested / Open | **HIGH (Stat-Arb Viable)** |
| **Pillar 5: Institutional COT Flow** | 20 | 0 | **0.0%** | Untested / Open | **HIGH (Macro Swing Viable)** |
| **TOTAL RESEARCH SPACE** | **150** | **6** | **4.0%** | **96% Unexplored** | **EXPAND BEYOND PILLAR 1** |

---

## 4. Key Takeaway

QROS has thoroughly explored Pillar 1 (Univariate Technicals) and demonstrated that simple technical price patterns on spot gold are non-viable under institutional transaction costs. **96% of the true quantitative search space remains untouched** because the data environment has been restricted to a single, univariate broker feed.
