# QROS Standard: Statistical Validation & Multiple Testing Standard
**Standard ID:** QROS-STD-STAT-005  
**File:** `05_STATISTICAL_VALIDATION_STANDARD.md`  
**Mission:** QROS-RESEARCH-001 (Amended by QROS-GOV-002)  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Statistical Philosophy: Beyond Naive p-Values

In quantitative finance, standard asymptotic tests (such as basic t-tests) frequently fail due to fat tails, skewness, temporal autocorrelation, and selection bias. QROS enforces rigorous non-parametric and distribution-free statistical verification.

> [!IMPORTANT]
> **Statistical Significance $\neq$ Economic Tradability**: A p-value $< 0.001$ with a 0.05 pip gross expectancy is economically worthless once bid-ask spreads and execution delays are accounted for. Both statistical *and* economic hurdles must be surpassed.

---

## 2. Quantitative Validation Requirements

Every candidate effect must undergo the following 6 statistical evaluations:

```
                  ┌──────────────────────────────────────────────┐
                  │         STATISTICAL VALIDATION SUITE         │
                  ├──────────────────────────────────────────────┤
                  │ 1. Class-Calibrated Sample Size ($N$ & $T$)  │
                  │ 2. Effect Size & Standardized Expectancy     │
                  │ 3. Bootstrap Confidence Intervals (95% CI)   │
                  │ 4. Deflated Sharpe Ratio (DSR > 0.95)        │
                  │ 5. Multiple Testing Adjustment (FDR / B-H)   │
                  │ 6. Tail Risk & Higher Moments (VaR / CVaR)   │
                  └──────────────────────────────────────────────┘
```

### 1. Sample Size & Statistical Power Calibration by Research Class
Statistical power and minimum sample sizes are strictly governed by the declared Research Class (per `02_RESEARCH_CLASS_SPECIFICATION.md`):

| Research Class | Min. Discrete Trades ($N$) | Min. Bar Count ($T$) | Min. Calendar Span | Min. Effective $N_{\text{eff}}$ |
| :--- | :--- | :--- | :--- | :--- |
| **CLASS-I: HF-MICRO** | $\mathbf{\ge 1,000}$ | $\ge 50,000$ (M1/M5) | $\ge 2$ Years | $\ge 500$ |
| **CLASS-II: INTRADAY-MOM**| $\mathbf{\ge 400}$ | $\ge 15,000$ (M5–H1) | $\ge 3$ Years | $\ge 200$ |
| **CLASS-III: SWING-STATARB**| $\mathbf{\ge 150}$ | $\ge 5,000$ (H1–D1) | $\ge 5$ Years | $\ge 80$ |
| **CLASS-IV: MACRO-REGIME** | $\mathbf{\ge 40}$ | $\ge 3,000$ (D1/W1) | $\ge 12$ Years (2 Cycles) | $\ge 30$ |
| **CLASS-V: CROSS-FACTOR** | $\mathbf{\ge 500}$ (Pooled) | $\ge 10,000$ (Panel) | $\ge 5$ Years | $\ge 250$ |

If trades exhibit serial autocorrelation, effective sample size $N_{\text{eff}} = \frac{N}{1 + 2 \sum_{k=1}^{\infty} \rho(k)}$ must satisfy the class minimum.

### 2. Effect Size & Expectancy Metrics
- Standardized Effect Size: Cohen's $d = \frac{\mu - \mu_0}{\sigma} \ge 0.25$.
- Net Profit Factor ($\text{PF}$): Calibrated by Research Class ($\text{CLASS-I} \ge 1.40$, $\text{CLASS-II} \ge 1.35$, $\text{CLASS-III} \ge 1.30$, $\text{CLASS-IV} \ge 1.50$, $\text{CLASS-V} \ge 1.30$) after all class-specific friction.
- Net Trade Expectancy: $\mathbb{E}[\text{Trade}] \ge 1.5 \times (\text{Class-Specific Spread} + \text{Slippage})$.

### 3. Bootstrap & Resampling Procedures
- **Stationary Bootstrap (Politis & Romano)**: Used to resample return time series while preserving block-dependency and serial autocorrelation.
- **Confidence Interval Hurdle**: The lower bound of the 95% Bootstrap Confidence Interval for Net Sharpe Ratio must remain strictly positive ($\text{CI}_{95\%}^{\text{lower}}(\text{SR}) > 0.0$).
- **Low-Frequency Adjustment (CLASS-IV)**: Uses Stationary Block Bootstrap ($B \ge 5,000$ iterations) to compensate for low event counts ($N \ge 40$).

### 4. Tail Risk & Higher Moment Verification
- **Skewness & Kurtosis**: Document return skewness ($S$) and excess kurtosis ($K$). Positive skewness preferred; heavy negative skewness ($S < -1.5$) triggers automatic risk escalation.
- **Value at Risk & Conditional VaR**: 99% 1-day Historical VaR and 99% Expected Shortfall (CVaR).

---

## 3. Multiple Testing & False Discovery Rate (FDR) Protocol

When hundreds or thousands of hypotheses, feature combinations, or parameter sets are tested, high Sharpe ratios inevitably arise purely by chance. QROS mandates explicit mathematical adjustments for data snooping.

### 1. Deflated Sharpe Ratio (DSR)
Every candidate's Sharpe Ratio ($\widehat{\text{SR}}$) must be deflated based on the total number of historical trials ($K$) tested within that research family (Bailey & López de Prado):

$$\text{DSR} = \Phi \left( \frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{T - 1}}{\sqrt{1 - \widehat{\gamma}_3 \widehat{\text{SR}} + \frac{\widehat{\gamma}_4 - 1}{4} \widehat{\text{SR}}^2}} \right)$$

Where:
- $\text{SR}^* = \sqrt{\frac{V(\{ \text{SR}_k \})}{2}} \left( (1 - \gamma) Z^{-1}(1 - \frac{1}{K}) + \gamma Z^{-1}(1 - \frac{1}{K e}) \right)$
- $K$: Total number of tested parameter / feature configurations.
- $T$: Number of observations (sample length).
- $\widehat{\gamma}_3, \widehat{\gamma}_4$: Sample skewness and kurtosis.

> **Institutional Acceptance Threshold**: $\mathbf{\text{DSR} \ge 0.95}$ (Probability that the observed Sharpe ratio is not a false positive exceeds 95%).

### 2. Benjamini-Hochberg (BH) Multiple Testing Correction
For batch hypothesis screening, p-values $p_{(1)} \le p_{(2)} \le \dots \le p_{(M)}$ must satisfy:

$$p_{(i)} \le \frac{i}{M} Q^* \quad (\text{with False Discovery Rate } Q^* = 0.05)$$

---

## 4. Mandatory Global Trial Tracking Ledger

QROS research systems must maintain continuous, transparent counters across all experiments. Unsuccessful experiments must **never** be deleted or hidden.

```
┌──────────────────────────────────────────────────────────┐
│             QROS GLOBAL EXPERIMENTATION LEDGER           │
├─────────────────────────────────────────────┬────────────┤
│ Total Hypotheses Generated                  │ Count      │
│ Total Hypotheses Tested                     │ Count      │
│ Total Feature Combinations Explored         │ Count      │
│ Total Parameter Variations Evaluated ($K$)  │ Count      │
│ Total Hypotheses Rejected                   │ Count      │
│ Total Promising Hypotheses                  │ Count      │
│ Total Edge Candidates Promoted              │ Count      │
│ Total Confirmed Edges Validated             │ Count      │
└─────────────────────────────────────────────┴────────────┘
```
