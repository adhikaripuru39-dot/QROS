# QROS Standard: Robustness & Perturbation Testing Standard
**Standard ID:** QROS-STD-ROB-007  
**File:** `07_ROBUSTNESS_STANDARD.md`  
**Mission:** QROS-RESEARCH-001 (Amended by QROS-GOV-002)  
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

*(Note: Numerical grids and thresholds below represent initial default baseline calibrations defined via Validation Profiles).*

### 1. Parameter Sensitivity & Plateau Analysis (No "Cliff-Edge" Edges)
- **Methodology**: Perturb all continuous model parameters across default class grids (or profile overrides):
  - `CLASS-I (HF-MICRO)`: $\pm 10\%, \pm 20\%$
  - `CLASS-II (INTRADAY-MOM)`: $\pm 15\%, \pm 25\%$
  - `CLASS-III (SWING-STATARB)`: $\pm 20\%, \pm 30\%$
  - `CLASS-IV (MACRO-REGIME)`: $\pm 25\%, \pm 40\%$
  - `CLASS-V (CROSS-FACTOR)`: $\pm 15\%, \pm 25\%$
- **Acceptance Rule**:
  - The parameter response surface must exhibit a smooth, convex plateau.
  - Performance must not drop by more than $30\%$ under minimum perturbation step.
  - Any isolated "needle-in-a-haystack" performance peak is classified as **Curve-Fitting Overfitting** and triggers immediate disqualification.

### 2. Temporal & Sub-Period Stability
- **Methodology**: Partition the historical dataset into contiguous, non-overlapping chronological epochs ($\ge 4$ epochs for Classes I–III and V; $\ge 2$ full multi-year economic cycles for Class IV).
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
- **Methodology**: Re-evaluate net returns under escalating class-specific friction:
  - `CLASS-I`: $3.0\times$ Base Spread, $4.0\times$ Base Slippage, $500\text{ms}$ execution latency delay.
  - `CLASS-II`: $2.0\times$ Base Spread, $2.5\times$ Base Slippage, $200\text{ms}$ execution latency delay.
  - `CLASS-III`: $1.5\times$ Base Spread, $2.0\times$ Base Slippage, full financing swap deduction.
  - `CLASS-IV`: $1.5\times$ Base Spread, institutional swap model, weekend gap risk model.
  - `CLASS-V`: $2.0\times$ Multi-leg synthetic execution spread & asynchronous leg fill delay.
- **Acceptance Rule**:
  - Net Expectancy must remain $> 0.0$ and Net Profit Factor $\ge 1.15$ under peak friction stress.

### 5. Cross-Asset Structural Transferability
- **Methodology**: Where theoretically justified by the underlying economic mechanism, evaluate the logic on economically correlated proxy instruments (e.g., testing an XAUUSD gold mechanism on XAGUSD silver, or EURUSD on GBPUSD).
- **Acceptance Rule**:
  - The proxy asset must show positive directional drift or supportive statistical resonance (confirming market phenomenon rather than asset-specific noise).

### 6. Walk-Forward Efficiency (WFE) & CPCV
- **Methodology**: Execute anchored and rolling Walk-Forward Optimization (WFO) and Combinatorial Purged Cross-Validation (CPCV).
- **Metric**: Walk-Forward Efficiency $\text{WFE} = \frac{\text{Annualized OOS Return}}{\text{Annualized IS Return}}$.
- **Acceptance Rule**:
  - $\text{CLASS-I} \ge 0.70$, $\text{CLASS-II} \ge 0.65$, $\text{CLASS-III} \ge 0.60$, $\text{CLASS-IV} \ge 0.55$, $\text{CLASS-V} \ge 0.65$ with zero negative walk-forward cycles.

### 7. Monte Carlo Permutation & Resampling
- **Methodology**: 10,000-iteration Monte Carlo permutation of trade order sequence and return distribution resampling without replacement.
- **Acceptance Rule**:
  - Probability of ultimate drawdown exceeding $25\%$ must be $< 1.0\%$.
  - 95th percentile simulated Max Drawdown must be within documented risk thresholds.
