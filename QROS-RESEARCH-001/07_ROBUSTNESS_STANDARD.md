# QROS Standard: Robustness & Perturbation Testing Standard
**Standard ID:** QROS-STD-ROB-007  
**File:** `07_ROBUSTNESS_STANDARD.md`  
**Mission:** QROS-RESEARCH-001  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Mandate & Objective

A candidate effect that performs well under nominal backtest parameters is assumed to be curve-fit until proven robust against environmental and structural perturbations. In accordance with QROS Stage 10 Governance, every Edge Candidate must survive a battery of 7 Stress & Robustness Tests before proceeding to Out-of-Sample confirmation.

```
                      ┌────────────────────────────────────────┐
                      │       7-DIMENSIONAL ROBUSTNESS SUITE   │
                      ├────────────────────────────────────────┤
                      │ 1. Parameter Sensitivity & Plateau Test│
                      │ 2. Temporal & Sub-Period Stability     │
                      │ 3. Market Regime Shift Resilience      │
                      │ 4. Transaction Cost & Slippage Stress  │
                      │ 5. Cross-Asset Structural Transfer     │
                      │ 6. Walk-Forward Efficiency (WFE)       │
                      │ 7. Monte Carlo Trade Resampling        │
                      └────────────────────────────────────────┘
```

---

## 2. Specification of Robustness Tests

### 1. Parameter Sensitivity & Plateau Analysis (No "Cliff-Edge" Edges)
- **Methodology**: Perturb all continuous model parameters across a $\pm 10\%$, $\pm 20\%$, and $\pm 30\%$ grid around the optimal configuration.
- **Acceptance Rule**:
  - The parameter response surface must exhibit a smooth, convex plateau.
  - Performance must not drop by more than $30\%$ under $\pm 10\%$ perturbation.
  - Any isolated "needle-in-a-haystack" performance peak is classified as **Curve-Fitting Overfitting** and triggers immediate disqualification.

### 2. Temporal & Sub-Period Stability
- **Methodology**: Partition the historical dataset into at least 4 contiguous, non-overlapping chronological epochs (e.g., 2018–2020, 2020–2022, 2022–2024, 2024–2026).
- **Acceptance Rule**:
  - Net Profit Factor must exceed $1.15$ in at least $80\%$ of sub-periods.
  - Maximum drawdown in any sub-period must not exceed $2.0 \times$ the full-sample expected drawdown.

### 3. Market Regime Shift Resilience
- **Methodology**: Segment evaluation periods by macroeconomic and volatility regimes:
  - High Volatility Expansion ($\text{ATR}_{14} > \text{Quantile}_{75}$)
  - Low Volatility Compression ($\text{ATR}_{14} < \text{Quantile}_{25}$)
  - Strong Trend vs. Mean-Reverting Choppy Range
- **Acceptance Rule**:
  - If the hypothesis is regime-specific, it must remain dormant with near-zero activity during out-of-regime periods.
  - If regime-agnostic, it must not suffer catastrophic collapse ($> 15\%$ loss) in any single regime.

### 4. Transaction Cost & Execution Delay Stress Test
- **Methodology**: Re-evaluate net returns under escalating friction:
  - Test 1: $1.5 \times$ Base Spread, $2.0 \times$ Base Slippage.
  - Test 2: $2.0 \times$ Base Spread, $3.0 \times$ Base Slippage.
  - Test 3: Simulated 500ms and 1,000ms latency execution delays (fill price shifted by next tick drift).
- **Acceptance Rule**:
  - Under Test 1, Net Profit Factor must remain $\ge 1.20$.
  - Under Test 2, Net Expectancy must remain $> 0.0$.

### 5. Cross-Asset Structural Transferability
- **Methodology**: Where theoretically justified by the underlying economic mechanism, evaluate the logic on economically correlated proxy instruments (e.g., testing an XAUUSD gold mechanism on XAGUSD silver, or EURUSD on GBPUSD).
- **Acceptance Rule**:
  - The proxy asset must show positive directional drift or supportive statistical resonance (confirming market phenomenon rather than asset-specific noise).

### 6. Walk-Forward Efficiency (WFE) & CPCV
- **Methodology**: Execute anchored and rolling Walk-Forward Optimization (WFO) and Combinatorial Purged Cross-Validation (CPCV).
- **Metric**: Walk-Forward Efficiency $\text{WFE} = \frac{\text{Annualized OOS Return}}{\text{Annualized IS Return}}$.
- **Acceptance Rule**: $\mathbf{\text{WFE} \ge 0.60}$ with zero negative walk-forward cycles.

### 7. Monte Carlo Permutation & Resampling
- **Methodology**: 10,000-iteration Monte Carlo permutation of trade order sequence and return distribution resampling without replacement.
- **Acceptance Rule**:
  - Probability of ultimate drawdown exceeding $25\%$ must be $< 1.0\%$.
  - 95th percentile simulated Max Drawdown must be within documented risk thresholds.
