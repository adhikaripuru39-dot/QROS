# QROS Standard: Hypothesis Framework & Quality Standard
**Standard ID:** QROS-STD-HYP-002  
**File:** `02_HYPOTHESIS_FRAMEWORK.md`  
**Mission:** QROS-RESEARCH-001 (Amended by QROS-GOV-002)  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Purpose & Core Mandate

In QROS, no quantitative experiment, backtest, or data analysis shall be conducted without an approved, registered hypothesis. Unstructured data mining ("p-hacking") is strictly prohibited. Every research inquiry must begin with a formal theoretical proposition that posits a testable cause-and-effect relationship in financial markets.

---

## 2. Hypothesis Identification Standard

Every hypothesis must be assigned a globally unique, sequential alphanumeric identifier formatted as:

$$\text{Format: } \mathbf{QROS\text{-}HYP\text{-}XXXXXX}$$
*(where XXXXXX is a zero-padded 6-digit integer, e.g., `QROS-HYP-000001`, `QROS-HYP-000002`)*

---

## 3. Mandatory 18-Field Hypothesis Schema

To ensure completeness, every hypothesis record must specify the following 18 structural fields:

| Field # | Field Name | Description & Institutional Requirement |
| :--- | :--- | :--- |
| **1** | `Hypothesis ID` | Unique identifier (`QROS-HYP-XXXXXX`). |
| **2** | `Market` | Target asset class (e.g., Commodities, Foreign Exchange, Equity Indices). |
| **3** | `Asset` | Specific ticker/instrument (e.g., `XAUUSD`, `EURUSD`, `US500`). |
| **4** | `Timeframe` | Primary sampling frequency (e.g., `M1`, `M5`, `H1`, `D1`). |
| **5** | `Validation Profile / Class`| Declared validation regime (`CLASS-I` through `CLASS-V`), bound Validation Profile, and market regime bounds. |
| **6** | `Observation` | The raw empirical noticing triggering this research inquiry. |
| **7** | `Hypothesis Statement` | Formal statement describing the conditional shift in asset return distribution. |
| **8** | `Plausible Mechanism / Rationale` | Documented economic, behavioral, or structural driver. Causal proof is not universally required; undocumented statistical coincidences receive an elevated validation burden. |
| **9** | `Entry Condition` | Unambiguous, deterministic mathematical trigger for state entry. |
| **10** | `Exit Condition` | Precise criteria for state termination (time-stop, volatility target, signal invalidation). |
| **11** | `Holding Period` | Maximum expected trade/event horizon in bars or time duration. |
| **12** | `Expected Effect` | Quantitative target (e.g., forward return distribution mean $> +0.15 \sigma$, directional skew). |
| **13** | `Null Hypothesis ($H_0$)` | Precise condition under which no effect exists (e.g., $\mu_{\text{return}} = 0$). |
| **14** | `Alternative Hypothesis ($H_1$)`| Precise condition demonstrating the existence of the effect (e.g., $\mu_{\text{return}} > 0$). |
| **15** | `Required Data` | Exact datasets, features, order book feeds, or macroeconomic calendar inputs needed. |
| **16** | `Potential Confounders` | Intervening variables (e.g., liquidity dry-up, central bank rate decisions, rollover spread). |
| **17** | `Transaction Cost Assumptions` | Spread, commissions, slippage, and swap model calibrated via the designated Validation Profile. |
| **18** | `Research Status` | Current state machine status (`DRAFT`, `REGISTERED`, `IN_PROGRESS`, `REJECTED`, `PROMISING`). |

---

## 4. Hypothesis Quality Standard (6 Non-Negotiable Criteria)

A proposed hypothesis will be rejected during Governance Review if it fails any of the following 6 quality tests:

```
                  ┌───────────────────────────────┐
                  │   HYPOTHESIS QUALITY GATES    │
                  ├───────────────────────────────┤
                  │  1. Specific                  │
                  │  2. Falsifiable               │
                  │  3. Mechanically Testable     │
                  │  4. Time-Bounded              │
                  │  5. Condition-Bounded         │
                  │  6. Quantifiable              │
                  └───────────────────────────────┘
```

1. **Specific**:
   - ❌ *Weak / Rejected*: "Gold tends to reverse after big moves."
   - ✅ *Strong / Accepted*: "Following an intraday 3-standard-deviation candle expansion on XAUUSD M5 during New York morning hours without macroeconomic headline releases, 15-minute mean forward return exhibits negative drift of at least 1.8 bps."
2. **Falsifiable**:
   - There must exist an explicit statistical outcome that decisively disproves the proposition (e.g., Student's t-test p-value $> 0.05$ or net expectancy $\le 0$).
3. **Mechanically Testable**:
   - Any quantitative researcher or algorithmic engine must be able to reproduce the exact test without human discretion, subjective chart interpretation, or undefined terms.
4. **Time-Bounded**:
   - The temporal window of the expected effect must be explicitly constrained (e.g., "within 30 minutes of London market open").
5. **Condition-Bounded**:
   - The hypothesis must define the exact market regime under which it operates, acknowledging regimes where the effect is inactive.
6. **Quantifiable**:
   - The effect must be measured using objective distributional statistics (forward mean return, Sharpe, Sortino, Deflated Sharpe Ratio) rather than visual inspection.

---

## 5. Standard Hypothesis Markdown Template

```markdown
# QROS Hypothesis Record: QROS-HYP-XXXXXX

- **Hypothesis ID:** QROS-HYP-XXXXXX
- **Title:** [Brief Descriptive Title]
- **Market:** [Commodities / FX / Indices / Crypto]
- **Asset:** [Ticker]
- **Timeframe:** [M1 / M5 / H1 / D1]
- **Validation Regime (Class):** [CLASS-I / CLASS-II / CLASS-III / CLASS-IV / CLASS-V]
- **Validation Profile:** [Default / Custom Profile ID]
- **Market Condition:** [Regime Definition]
- **Date Created:** YYYY-MM-DD
- **Author / Agent:** [Agent ID / Name]

### 1. Empirical Observation
[Describe the empirical observation triggering this inquiry]

### 2. Hypothesis Statement
[State the exact conditional proposition]

### 3. Economic / Structural / Behavioral Rationale
[Explain why this anomaly is plausible: Structural / Behavioral / Microstructure / Macroeconomic Flow]

### 4. Mathematical Definition & Conditions
- **Entry Trigger:** $f(X_t) > \theta$
- **Exit Criteria:** Time-stop = $N$ bars, or Stop-loss = $K \times \text{ATR}$
- **Holding Horizon:** $N$ bars

### 5. Statistical Hypotheses
- **Null Hypothesis ($H_0$):** $\mathbb{E}[R_{t+1:t+k} \mid \text{Trigger}] \le 0$
- **Alternative Hypothesis ($H_1$):** $\mathbb{E}[R_{t+1:t+k} \mid \text{Trigger}] > 0$

### 6. Data Requirements & Confounders
- **Required Datasets:** [Dataset IDs, versions, and features]
- **Potential Confounders:** [News events, session boundaries, low liquidity]
- **Transaction Cost Model:** Spread: $X$ pts, Commission: $Y$ / lot, Slippage: $Z$ pts

### 7. Governance Status
- **Current Status:** `REGISTERED`
- **Assigned Experiment:** `PENDING`
```
