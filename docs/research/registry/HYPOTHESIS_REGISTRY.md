# QROS Master Hypothesis Registry
**Last Updated:** 2026-08-15 04:51:24 UTC  
**Governing Standard:** QROS-STD-HYP-002  
**Status:** Formal Pre-Registration Baseline  

---

## 1. Registry Summary
- **Total Pre-Registered Hypotheses:** 6
- **Validation Architecture:** Governed by Class-Calibrated Validation Profiles (Classes I–V).
- **Integrity Rule:** All hypotheses are pre-registered *prior* to in-sample parameter fitting or backtest optimization.

---

## 2. Active Pre-Registered Hypotheses

| Hypothesis ID | Title | Asset | TF | Research Class | Status | Quality Gates |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`QROS-HYP-000001`](hypotheses/QROS-HYP-000001.yaml) | London Open Initial Balance Expansion and Intraday Momentum | XAUUSD | M5 | CLASS-II | `DATA INSUFFICIENT` | **[6/6 PASS]** |
| [`QROS-HYP-000002`](hypotheses/QROS-HYP-000002.yaml) | Multi-Hour Range Compression Breakout and Volatility Regime Transition | XAUUSD | H1 | CLASS-III | `DATA INSUFFICIENT` | **[6/6 PASS]** |
| [`QROS-HYP-000003`](hypotheses/QROS-HYP-000003.yaml) | Macro Mean Reversion Following 3-Sigma Daily Return Extensions | XAUUSD | D1 | CLASS-IV | `REJECTED` | **[6/6 PASS]** |
| [`QROS-HYP-000004`](hypotheses/QROS-HYP-000004.yaml) | Daily Macro 50-Day High Breakout Momentum Continuation | XAUUSD | D1 | CLASS-IV | `REJECTED` | **[6/6 PASS]** |
| [`QROS-HYP-000005`](hypotheses/QROS-HYP-000005.yaml) | Daily NR4 Range Compression to Multi-Day Volatility Expansion | XAUUSD | D1 | CLASS-IV | `REJECTED` | **[6/6 PASS]** |
| [`QROS-HYP-000006`](hypotheses/QROS-HYP-000006.yaml) | Cross-Timeframe Macro Trend Filtered Intraday Momentum | XAUUSD | H1 | CLASS-III | `DATA INSUFFICIENT` | **[6/6 PASS]** |

---

## 3. Detailed Hypothesis Specifications

### [QROS-HYP-000001] London Open Initial Balance Expansion and Intraday Momentum
- **Market / Asset / Timeframe:** COMMODITIES | XAUUSD | `M5`
- **Research Class:** `CLASS-II` (INTRADAY-MOM_DEFAULT)
- **Market Condition:** London Open Session (07:00-11:00 UTC) with Asian Range Compression
- **Empirical Observation:** Stylized Fact QROS-OBS-009 & QROS-OBS-010: Gold trading volume surges by 2.4x at London open (07:00 UTC), and the first 60-minute Initial Balance range is extended in 74% of sessions.
- **Hypothesis Statement:** Breakouts beyond the Asian session range (00:00-06:59 UTC high/low) occurring during the London opening window (07:00-09:00 UTC) with above-average volume exhibit positive directional momentum over a 60-180 minute holding horizon.
- **Economic / Microstructure Rationale:** Physical bullion fixing and European institutional order flow concentration trigger multi-hour directional liquidity drives, creating intraday momentum that persists until early New York overlap.
- **Entry Condition:** `Close of M5 bar crosses above Asian Session High (or below Asian Session Low) between 07:00 and 09:00 UTC, accompanied by M5 tick_volume > 1.5x 20-period moving average.`
- **Exit Condition:** `Fixed time exit at 11:00 UTC (pre-NY), or trailing volatility stop at 1.5x ATR(14), or opposite session boundary touch.`
- **Holding Period:** 12 to 36 M5 bars (1.0 to 3.0 hours)
- **Expected Effect:** Net annualized Sharpe >= 1.40, Profit Factor >= 1.40 under Class II 2.5x slippage stress and 200ms latency.
- **Null Hypothesis ($H_0$):** `H_0: Mean net return of London open breakout trades is <= 0.0 (or annualized Sharpe <= 0.0).`
- **Alternative Hypothesis ($H_1$):** `H_1: Mean net return of London open breakout trades is strictly > 0.0 with DSR score >= 0.95 at alpha = 0.05.`
- **Cost Assumptions:** Class II Profile: 25 pts nominal spread, 2.5x slippage multiplier, 200ms execution latency buffer.

---

### [QROS-HYP-000002] Multi-Hour Range Compression Breakout and Volatility Regime Transition
- **Market / Asset / Timeframe:** COMMODITIES | XAUUSD | `H1`
- **Research Class:** `CLASS-III` (SWING-STATARB_DEFAULT)
- **Market Condition:** Consolidation regime where ATR(6) / ATR(24) < 0.60 across active market sessions
- **Empirical Observation:** Stylized Fact QROS-OBS-002, QROS-OBS-003, & QROS-OBS-007: Realized volatility exhibits autoregressive clustering; periods of extreme range compression (ATR6/ATR24 < 0.60) precede persistent volatility expansion regimes.
- **Hypothesis Statement:** Directional breakouts from a multi-hour volatility compression state (ATR6/ATR24 < 0.60) on H1 persist in the direction of the breakout over an 8 to 24 hour holding window.
- **Economic / Microstructure Rationale:** Consolidation traps resting stop liquidity on both sides of the market. Once directional momentum breaches the range boundary, cascading stop execution and trend-following inflows fuel multi-hour expansion.
- **Entry Condition:** `H1 close breaks above the 24-hour high (or below 24-hour low) following at least 6 consecutive hours of ATR(6)/ATR(24) < 0.60 compression.`
- **Exit Condition:** `Exit after 16 H1 bars (16 hours), or upon trailing stop loss of 2.0x ATR(24), or when Garman-Klass volatility reaches 95th percentile.`
- **Holding Period:** 8 to 24 H1 bars (8 to 24 hours)
- **Expected Effect:** Net annualized Sharpe >= 1.20, Profit Factor >= 1.30 under Class III 2.0x slippage stress.
- **Null Hypothesis ($H_0$):** `H_0: Post-compression breakout returns do not differ from zero (E[R_net] <= 0).`
- **Alternative Hypothesis ($H_1$):** `H_1: Post-compression breakout returns are strictly positive (E[R_net] > 0) with DSR >= 0.95 under multiple-testing accounting.`
- **Cost Assumptions:** Class III Profile: 20 pts nominal spread, 2.0x slippage multiplier, 0ms latency buffer.

---

### [QROS-HYP-000003] Macro Mean Reversion Following 3-Sigma Daily Return Extensions
- **Market / Asset / Timeframe:** COMMODITIES | XAUUSD | `D1`
- **Research Class:** `CLASS-IV` (MACRO-REGIME_DEFAULT)
- **Market Condition:** Macro trend extension where Daily Close deviates > 3.0 standard deviations from 50-day moving average
- **Empirical Observation:** Stylized Fact QROS-OBS-001, QROS-OBS-006, & QROS-OBS-014: Gold return distributions exhibit severe kurtosis (8.91) and Ornstein-Uhlenbeck mean-reversion forces when price stretches to extreme standard deviations.
- **Hypothesis Statement:** Daily closes exceeding 3.0 rolling standard deviations from the 50-day moving average exhibit statistical mean-reversion drift back toward the 20-day mean over a 3 to 10 day horizon.
- **Economic / Microstructure Rationale:** Overextended price moves exhaust aggressive speculative buying/selling power, prompting institutional profit-taking and inventory rebalancing by bullion market makers.
- **Entry Condition:** `Daily close > MA(50) + 3.0 * Std(50) for short mean-reversion, or Daily close < MA(50) - 3.0 * Std(50) for long mean-reversion.`
- **Exit Condition:** `Daily close crosses back across the 20-day moving average, or time stop at 10 trading days, or stop loss at 1.5x entry ATR.`
- **Holding Period:** 3 to 10 D1 bars (3 to 10 trading days)
- **Expected Effect:** Net annualized Sharpe >= 1.00, Profit Factor >= 1.25 under Class IV macro hurdles.
- **Null Hypothesis ($H_0$):** `H_0: Mean return of extreme deviation trades is <= 0.0.`
- **Alternative Hypothesis ($H_1$):** `H_1: Mean return of extreme deviation trades is strictly > 0.0 with DSR >= 0.95.`
- **Cost Assumptions:** Class IV Profile: 20 pts spread, 1.5x slippage multiplier, 0ms latency buffer.

---

### [QROS-HYP-000004] Daily Macro 50-Day High Breakout Momentum Continuation
- **Market / Asset / Timeframe:** COMMODITIES | XAUUSD | `D1`
- **Research Class:** `CLASS-IV` (MACRO-REGIME_DEFAULT)
- **Market Condition:** Macro trend expansion regime where Daily Close exceeds the prior 50-day highest high
- **Empirical Observation:** Stylized Fact QROS-OBS-019 & Pattern QROS-PAT-001: Gold 5-day forward log return averages +0.72% following a 50-day high breakout across 14 years of macro data (N=186, p < 0.001).
- **Hypothesis Statement:** Daily closes exceeding the prior 50-day highest high in Gold initiate multi-day upward momentum continuation with positive expected return over a 5 to 20 trading day holding period.
- **Economic / Microstructure Rationale:** Gold is a non-yielding monetary reserve asset. Long-term technical breakouts attract institutional asset allocation, central bank accumulation, and CTA momentum chasing that persist over multi-week horizons.
- **Entry Condition:** `Daily Close > Prior 50-Day Highest High (shifted by 1 for point-in-time) with 50-Day MA slope > 0.`
- **Exit Condition:** `Exit after 15 D1 bars (15 trading days), or trailing stop loss of 2.0x ATR(20), or when daily close crosses below 20-day moving average.`
- **Holding Period:** 5 to 20 D1 bars (5 to 20 trading days)
- **Expected Effect:** Net annualized Sharpe >= 1.00, Profit Factor >= 1.30 under Class IV macro hurdles.
- **Null Hypothesis ($H_0$):** `H_0: Mean forward return of 50-day high breakout trades is <= 0.0.`
- **Alternative Hypothesis ($H_1$):** `H_1: Mean forward return of 50-day high breakout trades is strictly > 0.0 with DSR >= 0.90 under multiple testing accounting.`
- **Cost Assumptions:** Class IV Profile: 20 pts spread, 1.5x slippage multiplier, 0ms latency buffer.

---

### [QROS-HYP-000005] Daily NR4 Range Compression to Multi-Day Volatility Expansion
- **Market / Asset / Timeframe:** COMMODITIES | XAUUSD | `D1`
- **Research Class:** `CLASS-IV` (MACRO-REGIME_DEFAULT)
- **Market Condition:** Multi-day volatility compression regime where Daily True Range is the narrowest of the last 4 days (NR4)
- **Empirical Observation:** Stylized Fact QROS-OBS-020 & Pattern QROS-PAT-002: Daily NR4 compression precedes a 38% increase in 3-day realized price dispersion across 14 years (N=312, p < 0.001).
- **Hypothesis Statement:** Directional breakouts from a 4-day range compression (NR4) on D1 continue in the direction of the initial daily breakout over a 3 to 8 day holding window.
- **Economic / Microstructure Rationale:** Multi-day range compression reflects temporary supply-demand equilibrium and volatility suppression. When directional order flow breaches the compression boundary, resting stops and momentum participants accelerate expansion.
- **Entry Condition:** `Daily True Range < Min(True Range of prior 3 days) [NR4], followed on day t+1 by price breaking above NR4 High (Long) or below NR4 Low (Short).`
- **Exit Condition:** `Exit after 5 D1 bars (5 trading days), or upon 1.5x ATR(20) trailing stop loss.`
- **Holding Period:** 3 to 8 D1 bars (3 to 8 trading days)
- **Expected Effect:** Net annualized Sharpe >= 1.00, Profit Factor >= 1.25 under Class IV macro hurdles.
- **Null Hypothesis ($H_0$):** `H_0: Mean net return of post-NR4 breakout trades is <= 0.0.`
- **Alternative Hypothesis ($H_1$):** `H_1: Mean net return of post-NR4 breakout trades is strictly > 0.0 with DSR >= 0.90.`
- **Cost Assumptions:** Class IV Profile: 20 pts spread, 1.5x slippage multiplier, 0ms latency buffer.

---

### [QROS-HYP-000006] Cross-Timeframe Macro Trend Filtered Intraday Momentum
- **Market / Asset / Timeframe:** COMMODITIES | XAUUSD | `H1`
- **Research Class:** `CLASS-III` (SWING-STATARB_DEFAULT)
- **Market Condition:** Hourly breakout aligned with Daily 50-day Macro Moving Average trend direction
- **Empirical Observation:** Stylized Fact QROS-OBS-022 & Pattern QROS-PAT-006: H1 24-period breakouts aligned with D1 50-day trend direction produce positive 8-hour forward drift across non-OOS data (N=84, p = 0.012).
- **Hypothesis Statement:** H1 24-bar high/low breakouts that strictly align with the higher-timeframe Daily macro trend (D1 Close > MA50) exhibit positive directional drift over an 8 to 24 hour holding window.
- **Economic / Microstructure Rationale:** Higher-timeframe macro trend alignment filters out false consolidation whipsaws by ensuring lower-timeframe breakout momentum flows in the direction of institutional macro positioning.
- **Entry Condition:** `H1 Close > 24-bar High AND D1 Close > 50-Day MA (Long); H1 Close < 24-bar Low AND D1 Close < 50-Day MA (Short).`
- **Exit Condition:** `Exit after 16 H1 bars (16 hours), or trailing stop at 2.0x ATR(24).`
- **Holding Period:** 8 to 24 H1 bars (8 to 24 hours)
- **Expected Effect:** Net annualized Sharpe >= 1.20, Profit Factor >= 1.30 under Class III swing hurdles.
- **Null Hypothesis ($H_0$):** `H_0: Mean net return of trend-aligned H1 breakouts is <= 0.0.`
- **Alternative Hypothesis ($H_1$):** `H_1: Mean net return of trend-aligned H1 breakouts is strictly > 0.0 with DSR >= 0.95.`
- **Cost Assumptions:** Class III Profile: 20 pts spread, 2.0x slippage multiplier, 0ms latency buffer.

---
