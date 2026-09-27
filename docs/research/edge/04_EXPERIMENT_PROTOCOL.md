# QROS Standard: Experiment Protocol & Leakage Controls
**Standard ID:** QROS-STD-EXP-004  
**File:** `04_EXPERIMENT_PROTOCOL.md`  
**Mission:** QROS-RESEARCH-001  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Experimentation Mandate

In QROS, no undocumented, unversioned, or ad-hoc backtest shall be recognized as valid quantitative research. Every experiment must execute under a strictly controlled protocol linked to a parent Hypothesis ID (`QROS-HYP-XXXXXX`) and recorded under a unique Experiment ID formatted as:

$$\text{Format: } \mathbf{QROS\text{-}EXP\text{-}XXXXXX}$$

---

## 2. Mandatory 19-Field Experiment Record Schema

Every experiment artifact registered in QROS must document the following 19 parameters:

| Field # | Field Name | Description & Specification |
| :--- | :--- | :--- |
| **1** | `Experiment ID` | Unique ID (`QROS-EXP-XXXXXX`). |
| **2** | `Hypothesis ID` | Parent registered hypothesis (`QROS-HYP-XXXXXX`). |
| **3** | `Dataset Version / Hash` | SHA-256 hash and immutable version string of input data. |
| **4** | `Research Period` | Full historical date range examined ($T_{\text{start}} \dots T_{\text{end}}$). |
| **5** | `Training Period (In-Sample)` | Date range used for feature fitting and calibration. |
| **6** | `Validation Period` | Date range used for parameter stability and cross-validation. |
| **7** | `Test Period (Final OOS)` | Strictly embargoed out-of-sample date range tested once. |
| **8** | `Feature Definitions` | Precise formulas and lookback lengths of all features. |
| **9** | `Signal Definition` | Mathematical mapping from features to entry/exit states. |
| **10** | `Entry Execution Rules` | Order type, tick trigger, fill price assumption (next bar open/bid/ask). |
| **11** | `Exit Execution Rules` | Target, stop-loss, time-based exit, or signal decay rules. |
| **12** | `Holding Period` | Distribution of trade duration (mean, median, max bars). |
| **13** | `Direct Costs & Fees` | Round-turn commission and asset swap/financing rates. |
| **14** | `Slippage Assumptions` | Volatility-adjusted execution delay and spread widening penalty. |
| **15** | `Position Sizing Rules` | Fixed fractional or volatility-standardized allocation model. |
| **16** | `Evaluation Metrics` | Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor, Expectancy. |
| **17** | `Statistical Tests` | Student's t, Bootstrap CI, Permutation Test, Deflated Sharpe Ratio. |
| **18** | `Result Summary` | Quantitative performance breakdown across IS, Val, and OOS splits. |
| **19** | `Conclusion` | Categorical decision (`REJECTED`, `PROMISING`, `INCONCLUSIVE`). |

---

## 3. Strict Data Leakage Prevention Controls

Data leakage artificially inflates backtest metrics and destroys real-world performance. QROS implements an uncompromising 8-point Data Leakage Prevention Protocol:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   DATA LEAKAGE AUDIT CHECKLIST                         │
├────────────────────────────────────────────────────────────────────────┤
│ [ ] 1. Look-Ahead Bias: Signals at bar t use only data up to bar t.   │
│ [ ] 2. Feature Alignment: Shifting operations explicitly lagged (t-1). │
│ [ ] 3. Normalization Leakage: Scalers fitted exclusively on Train set. │
│ [ ] 4. Timestamp Precision: Timestamps normalized strictly to UTC.     │
│ [ ] 5. Purging & Embargoing: Overlapping trade labels purged.         │
│ [ ] 6. Survivorship Bias: Delisted / historical constituents included. │
│ [ ] 7. Selection Bias: Hypotheses formulated prior to OOS inspection.  │
│ [ ] 8. Final OOS Protection: Test set accessed only once at Gate 11.   │
└────────────────────────────────────────────────────────────────────────┘
```

### Specific Operational Rules:
1. **Look-Ahead Bias Elimination**:
   - Signal calculation for bar $t$ must only access information known at or before timestamp $t$. If an indicator depends on the close of bar $t$, execution cannot assume a fill price equal to the close of bar $t$; it must execute at the open of bar $t+1$ plus slippage.
2. **Normalization & Preprocessing Isolation**:
   - Rolling Z-scores, Min-Max scalers, and PCA transformations must compute mean and standard deviation strictly using historical rolling windows or In-Sample (IS) training segments. Future sample statistics must never contaminate historical standardization.
3. **Purging and Embargoing**:
   - In cross-validation, training samples that temporally overlap with the holding periods of test labels must be **purged**. An additional **embargo** buffer (minimum 10 bars or 1 full holding horizon) must be inserted between splits to eliminate autocorrelation leakage.

---

## 4. Multi-Tier Data Splitting Architecture

QROS divides historical data into 4 distinct chronological partitions (with percentages reflecting the initial default baseline):

```
[ Historical Data Stream ]
   │
   ├──► Tier 1: Discovery & Exploratory Data Analysis (EDA) [Default: 20%]
   │
   ├──► Tier 2: Model Development & In-Sample Training (IS) [Default: 40%]
   │
   ├──► Tier 3: Cross-Validation & Robustness Tuning (Val)  [Default: 20%]
   │
   └──► Tier 4: Protected Final Out-of-Sample Test (OOS)   [Default: 20%]
        └───► MANDATORY VAULTED PARTITION TESTED ONCE AT GATE 11
```

> [!IMPORTANT]
> **Tier 4 OOS Protection Rule**: A protected final OOS partition is a mandatory Universal Invariant. A 20% allocation is the standard default baseline; alternative allocations are permitted if explicitly documented and justified by the research design in the registered hypothesis. Iterative parameter optimization or repeated trial evaluations on Tier 4 data are grounds for immediate invalidation of the entire research project.

---

## 5. Realistic Transaction Cost & Friction Standard

Gross profitability is irrelevant. An edge exists only if it generates net profits after realistic institutional market friction:

$$\text{Net Return} = \text{Gross Return} - (\text{Spread} + \text{Commission} + \text{Slippage} + \text{Financing})$$

### Mandatory Friction Benchmarks:
- **XAUUSD (Spot Gold)**:
  - Spread: Minimum 15–25 pts ($0.15–$0.25) depending on session.
  - Slippage: Minimum 5–10 pts added during regular hours; 30–100 pts during economic releases.
  - Commission: Minimum $5.00 – $7.00 per round-turn standard lot.
- **Major FX**:
  - Spread: Minimum 0.6 – 1.5 pips.
  - Slippage: Minimum 0.5 – 2.0 pips.
  - Commission: Minimum $5.00 – $6.00 per round-turn standard lot.
