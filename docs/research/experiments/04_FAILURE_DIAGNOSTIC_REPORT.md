# QROS Hypothesis Failure Diagnostic & Attribution Report
**Date:** 2026-08-15 04:33:55 UTC  
**Asset:** XAUUSD  
**Mission:** QROS-RESEARCH-007  
**Framework Standard:** 8-Point Root-Cause Failure Attribution Protocol  

---

## 1. Diagnostic Framework & Root-Cause Dimensions
Every inconclusive or rejected hypothesis in QROS undergoes systematic diagnostic attribution across eight distinct quantitative vectors:
1. **Data Insufficiency ($T$ / Span):** Total observations or calendar duration fail to meet class minimums.
2. **Event Frequency Insufficiency ($N$ / $N_{\text{eff}}$):** Strategy produces too few discrete trades for statistical power.
3. **Underlying Economic Effect Weakness:** Gross return distribution lacks directional drift or statistical edge.
4. **Transaction Friction Destruction:** Strategy is profitable gross, but spread/slippage friction degrades net performance below hurdle.
5. **Statistical Uncertainty & Lack of Power:** Wide bootstrap confidence intervals spanning negative values or failing DSR ($K$).
6. **Regime & Distributional Instability:** High variance across sub-periods, heavy left-tail risk, or excess kurtosis.
7. **Hypothesis Specification Flaws:** Holding horizon, entry filters, or trailing stops misaligned with microstructure behavior.
8. **External Feed / Source Limitations:** Hard historical boundaries imposed by upstream broker feeds (e.g. 10k bar server cap).

---

## 2. Hypothesis-by-Hypothesis Diagnostic Attribution

### A. QROS-HYP-000001 (London Open Breakout, M5, Class II)
- **Outcome:** **`DATA INSUFFICIENT`**
- **Trade Sample ($N$):** $N = 7$ trades ($N_{\text{eff}} = 7.0$) vs. Required $N_{\text{min}} = 400$
- **Calendar Span:** $0.12$ years (41.6 days) vs. Required $\text{Span}_{\text{min}} = 3.0$ years
- **Observations ($T$):** $T = 8,000$ bars vs. Required $T_{\text{min}} = 15,000$
- **Gross vs. Net Performance:** Gross PF = 1.61, Net PF = 1.45, Net Sharpe = 2.24

#### Diagnostic Analysis:
- **Primary Cause: Feed Limitation & Data Insufficiency (Vectors 1 & 8):** The MT5 broker server hard-caps M5 history to 10,000 bars. Even utilizing 100% of available Non-OOS history (8,000 bars), only 41.6 trading days are covered, yielding a sample of only 7 valid London breakout events.
- **Secondary Cause: Statistical Uncertainty (Vector 5):** With $N=7$, the 95% bootstrap CI [-6.87, +8.12] is massive, spanning deep into negative expectation. The small sample renders any positive Sharpe ratio statistically untrustworthy.
- **Tertiary Cause: Transaction Friction Vulnerability (Vector 4):** Under 2.5x slippage stress and 200ms latency, transaction friction degrades gross PF from 1.61 to net PF of 1.45.
- **Recommendation:** **ABANDON FROM IMMEDIATE PRODUCTION.** Intraday momentum on M5 cannot be verified on this broker feed until a deep multi-year institutional tick/M1 archive is acquired.

---

### B. QROS-HYP-000002 (Volatility Compression Breakout, H1, Class III)
- **Outcome:** **`DATA INSUFFICIENT`**
- **Trade Sample ($N$):** $N = 0$ trades ($N_{\text{eff}} = 1.0$) vs. Required $N_{\text{min}} = 150$
- **Calendar Span:** $1.36$ years vs. Required $\text{Span}_{\text{min}} = 5.0$ years
- **Observations ($T$):** $T = 8,000$ bars vs. Required $T_{\text{min}} = 5,000$ [PASS on raw bars, FAIL on span]
- **Gross vs. Net Performance:** Gross PF = 1.00, Net PF = 1.00, Net Sharpe = 0.00

#### Diagnostic Analysis:
- **Primary Cause: Event Frequency & Span Insufficiency (Vectors 1 & 2):** Extreme multi-hour volatility compression ($\text{ATR}_6/\text{ATR}_{24} < 0.65$ sustained for $\ge 6$ consecutive hours followed by immediate 24-hour range breakout) did not occur in the non-OOS 1.36-year sample. The regime filter is too restrictive for short datasets.
- **Secondary Cause: Feed Limitation (Vector 8):** The 10,000-bar MT5 limitation caps H1 history to 500 calendar days, preventing observation across diverse multi-year volatility cycles.
- **Recommendation:** **PRESERVE FOR FUTURE EXPANDED TESTING.** Do not promote to Edge Candidate, but retain exact specification for re-evaluation if multi-decade H1 data becomes accessible.

---

### C. QROS-HYP-000003 (Daily 3-Sigma Mean Reversion, D1, Class IV)
- **Outcome:** **`REJECTED`**
- **Trade Sample ($N$):** $N = 65$ trades ($N_{\text{eff}} = 41.2$) vs. Required $N_{\text{min}} = 40$ [PASS]
- **Calendar Span:** $13.97$ years (2009 to 2023) vs. Required $\text{Span}_{\text{min}} = 12.0$ years [PASS]
- **Observations ($T$):** $T = 3,600$ daily bars vs. Required $T_{\text{min}} = 3,000$ [PASS]
- **Gross vs. Net Performance:** Gross PF = 0.65, Net PF = 0.63, Net Sharpe = -2.88

#### Diagnostic Analysis:
- **Primary Cause: Weak Underlying Economic Effect (Vector 3):** Across 14 years of macro data (3,600 bars), 3-sigma daily extensions in Gold do NOT exhibit mean reversion back to the 20-day mean. In precious metals, 3-sigma daily extensions represent runaway momentum or structural regime transitions (e.g. monetary crises, central bank gold buying) where counter-trend fading suffers severe losses.
- **Secondary Cause: Hypothesis Specification Flaw (Vector 7):** Fading 3-sigma daily moves on XAUUSD without a trend exhaustion or regime filter incurs catastrophic drawdown (Gross PF = 0.65, Net PF = 0.63).
- **Tertiary Cause: Statistical Rejection (Vector 5):** Bootstrap 95% CI is [-8.59, +1.49], Net Sharpe is -2.88, and DSR score is 0.000, failing all performance hurdles.
- **Recommendation:** **FORMALLY REJECTED.** Fading raw 3-sigma daily moves on Gold is empirically and economically falsified as a standalone statistical edge.

---

## 3. Summary Diagnostic Decision Matrix

| Hypothesis ID | Timeframe | Outcome | Dominant Root Cause | Scientific Disposition | Next Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `QROS-HYP-000001` | M5 | **`DATA INSUFFICIENT`** | Feed Truncation (10k bars) & Tiny Sample ($N=7$) | Structurally Untestable on MT5 | Suspend M5 research on current feed |
| `QROS-HYP-000002` | H1 | **`DATA INSUFFICIENT`** | Zero Event Occurrences in 1.36 yrs ($N=0$) | Over-Restrained Filter for Short Span | Queue for external data acquisition |
| `QROS-HYP-000003` | D1 | **`REJECTED`** | Economic Mechanism Failure (Trend Runaway vs Reversion) | Falsified by 14 Years of Real Macro Data | Archive as formal negative finding |