# QROS Standard: Research-Class Specification & Validation Profile Architecture
**Standard ID:** QROS-GOV-CLASS-003  
**Document:** `02_RESEARCH_CLASS_SPECIFICATION.md`  
**Mission:** QROS-GOV-002 (Finalized)  
**Status:** Mandatory Institutional Governance Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Executive Purpose: Validation Regimes

To maintain rigorous statistical power without inappropriately excluding legitimate quantitative strategies, QROS establishes **5 Canonical Validation Regimes** (referred to as **Research Classes**). 

> [!IMPORTANT]
> **Validation Regimes $\neq$ Theoretical Restrictions**: Research Classes do not restrict the types of market phenomena, instruments, or anomalies that QROS may research. Instead, they define the **appropriate statistical validation environment**, sampling expectations, and stress-testing protocols required for different holding periods and market frequencies.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      QROS 5 CANONICAL VALIDATION REGIMES                    │
├───────────┬───────────────────────────────┬──────────────┬──────────────────┤
│ Class ID  │ Validation Regime Name        │ Primary Freq │ Typical Horizon  │
├───────────┼───────────────────────────────┼──────────────┼──────────────────┤
│ CLASS-I   │ Microstructure & High-Freq    │ Tick, M1, M5 │ < 2 Hours        │
│ CLASS-II  │ Intraday Session & Momentum   │ M5, M15, H1  │ 2 – 12 Hours     │
│ CLASS-III │ Swing & Multi-Day Arbitrage   │ H1, H4, D1   │ 1 – 5 Days       │
│ CLASS-IV  │ Macro & Structural Regime     │ D1, W1       │ Weeks – Months   │
│ CLASS-V   │ Cross-Sectional Panel Factor  │ Multi-Asset  │ Hours – Weeks    │
└───────────┴───────────────────────────────┴──────────────┴──────────────────┘
```

---

## 2. Configuration-Driven Validation Profile Architecture

To decouple quantitative calibration values from the downstream statistical and execution core, QROS defines the **Validation Profile**:

```
┌────────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
│  Hypothesis Record │ ----> │   Validation Profile   │ ----> │   Statistical Engine   │
│ (Declared Class &  │       │ (Declarative YAML/JSON │       │ (Executes DSR, CPCV,   │
│  Regime Parameter) │       │  Calibration Schema)   │       │  Bootstrap, Costs)     │
└────────────────────┘       └────────────────────────┘       └────────────────────────┘
```

### Validation Profile Responsibilities:
1. **Declarative Configuration**: A Validation Profile is a versioned parameter set passed to the statistical engine for empirical evaluation.
2. **Default vs. Custom Calibration**: The tables in Section 3 and Section 4 provide the **initial default calibration baseline**. A hypothesis may specify custom profile parameters if supported by an explicit scientific justification in the registered hypothesis dossier.
3. **Reproducibility Contract**: The exact Validation Profile configuration is hashed (`SHA-256`) and recorded in the experiment record (`QROS-EXP-XXXXXX`).

---

## 3. Validation Regime Specification Profiles (Initial Default Calibrations)

*(Note: All numerical values listed below represent initial default baseline calibrations).*

### Class I: Microstructure & High-Frequency (`CLASS-I: HF-MICRO`)
- **Validation Focus**: Liquidity consumption, fill latency, tick imbalances, execution friction.
- **Typical Sampling Frequency**: `Tick`, `M1`, `M5`.
- **Expected Holding Period**: $< 2$ Hours (flat before session close).
- **Default Min. Discrete Trades ($N$)**: $\mathbf{N \ge 1,000}$ trades.
- **Default Min. Observations ($T$)**: $\mathbf{T \ge 50,000}$ bars across $\ge 2$ calendar years.
- **Default Performance Hurdles**: Net $\text{PF} \ge 1.40$, Net Sharpe $\ge 1.8$, Profile $\text{DSR} \ge 0.95$.
- **Default Friction Stress Model**: $3.0\times$ Base Spread, $4.0\times$ Base Slippage, $500\text{ms}$ execution latency delay.
- **Primary Failure Diagnostics**: Execution Mirage, Latency Decay.

### Class II: Intraday Session & Momentum (`CLASS-II: INTRADAY-MOM`)
- **Validation Focus**: Session open volatility, range expansion, macroeconomic release drift.
- **Typical Sampling Frequency**: `M5`, `M15`, `H1`.
- **Expected Holding Period**: $2\text{h} \dots 12\text{h}$ (zero overnight holding risk).
- **Default Min. Discrete Trades ($N$)**: $\mathbf{N \ge 400}$ trades.
- **Default Min. Observations ($T$)**: $\mathbf{T \ge 15,000}$ bars across $\ge 3$ calendar years.
- **Default Performance Hurdles**: Net $\text{PF} \ge 1.35$, Net Sharpe $\ge 1.4$, Profile $\text{DSR} \ge 0.95$.
- **Default Friction Stress Model**: $2.0\times$ Base Spread, $2.5\times$ Base Slippage.
- **Primary Failure Diagnostics**: Session Transition Whipsaw, Spread Expansion during illiquid rollovers.

### Class III: Swing & Multi-Day Arbitrage (`CLASS-III: SWING-STATARB`)
- **Validation Focus**: Multi-day mean reversion, cointegration stability, swing channel momentum.
- **Typical Sampling Frequency**: `H1`, `H4`, `D1`.
- **Expected Holding Period**: $1 \dots 5$ trading days (overnight holding permitted).
- **Default Min. Discrete Trades ($N$)**: $\mathbf{N \ge 150}$ trades.
- **Default Min. Observations ($T$)**: $\mathbf{T \ge 5,000}$ bars across $\ge 5$ calendar years.
- **Default Performance Hurdles**: Net $\text{PF} \ge 1.30$, Net Sharpe $\ge 1.2$, Profile $\text{DSR} \ge 0.95$.
- **Default Friction Stress Model**: $1.5\times$ Base Spread, $2.0\times$ Base Slippage, full financing swap deduction.
- **Primary Failure Diagnostics**: Cointegration Breakdown, Parameter Plateau Fragility.

### Class IV: Macro & Structural Regime (`CLASS-IV: MACRO-REGIME`)
- **Validation Focus**: Monetary policy divergence, yield curve shifts, multi-month economic trends.
- **Typical Sampling Frequency**: `D1`, `W1`.
- **Expected Holding Period**: $10 \dots 90$ trading days (weeks to months).
- **Default Min. Discrete Trades ($N$)**: $\mathbf{N \ge 40}$ discrete structural trades.
- **Default Supplementary Power Requirement**: $\mathbf{T \ge 3,000}$ daily observation bars across $\ge 12$ calendar years (spanning at least 2 full economic cycles) with non-parametric block bootstrap validation.
- **Default Performance Hurdles**: Net $\text{PF} \ge 1.50$, Net Sharpe $\ge 1.0$, Small-sample profile $\text{DSR} \ge 0.90$.
- **Default Friction Stress Model**: $1.5\times$ Base Spread, institutional swap financing model, weekend gap risk modeling.
- **Primary Failure Diagnostics**: Regime Sample Paucity, Structural Paradigm Shift.

### Class V: Cross-Sectional Panel Factor (`CLASS-V: CROSS-FACTOR`)
- **Validation Focus**: Factor premia, basket relative value, cross-asset dispersion.
- **Typical Sampling Frequency**: `M15`, `H1`, `D1` across $M \ge 5$ instruments.
- **Expected Holding Period**: Hours to Weeks.
- **Default Min. Discrete Trades ($N$)**: $\mathbf{N \ge 500}$ pooled panel trades ($N_{\text{per asset}} \ge 50$).
- **Default Min. Observations ($T$)**: $\mathbf{T \ge 10,000}$ panel bars across $\ge 5$ calendar years.
- **Default Performance Hurdles**: Net $\text{PF} \ge 1.30$, Panel $t$-statistic $> 3.5$, Profile $\text{DSR} \ge 0.95$.
- **Default Friction Stress Model**: Multi-leg synthetic execution spread & asynchronous leg fill latency.
- **Primary Failure Diagnostics**: Leg Execution Desynchronization, Cross-Correlation Inversion.

---

## 4. Master Validation Regime Parameter Matrix (Initial Default Baseline)

| Quantitative Parameter | Class I: HF-MICRO | Class II: INTRADAY-MOM | Class III: SWING-STATARB | Class IV: MACRO-REGIME | Class V: CROSS-FACTOR |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Frequency** | Tick / M1 / M5 | M5 / M15 / H1 | H1 / H4 / D1 | D1 / W1 | Panel Multi-Asset |
| **Typical Horizon** | $< 2$ Hours | 2 – 12 Hours | 1 – 5 Days | Weeks – Months | Hours – Weeks |
| **Default Min. Trades ($N$)** | $\mathbf{\ge 1,000}$ | $\mathbf{\ge 400}$ | $\mathbf{\ge 150}$ | $\mathbf{\ge 40}$ | $\mathbf{\ge 500}$ (Pooled) |
| **Default Min. Bars ($T$)** | $\mathbf{\ge 50,000}$ | $\mathbf{\ge 15,000}$ | $\mathbf{\ge 5,000}$ | $\mathbf{\ge 3,000}$ | $\mathbf{\ge 10,000}$ |
| **Default Min. Calendar Span**| $\ge 2$ Years | $\ge 3$ Years | $\ge 5$ Years | $\ge 12$ Years (2 Cycles) | $\ge 5$ Years |
| **Default Net Profit Factor** | $\ge 1.40$ | $\ge 1.35$ | $\ge 1.30$ | $\ge 1.50$ | $\ge 1.30$ |
| **Default Net Sharpe** | $\ge 1.80$ | $\ge 1.40$ | $\ge 1.20$ | $\ge 1.00$ | $\ge 1.30$ |
| **Default Profile DSR Hurdle** | $\ge 0.95$ | $\ge 0.95$ | $\ge 0.95$ | $\ge 0.90$ (Adjusted) | $\ge 0.95$ |
| **Default Walk-Forward (WFE)**| $\ge 0.70$ | $\ge 0.65$ | $\ge 0.60$ | $\ge 0.55$ | $\ge 0.65$ |
| **Default Perturbation Grid** | $\pm 10\%, \pm 20\%$ | $\pm 15\%, \pm 25\%$ | $\pm 20\%, \pm 30\%$ | $\pm 25\%, \pm 40\%$ | $\pm 15\%, \pm 25\%$ |
| **Spread Stress Multiplier** | $3.0\times$ | $2.0\times$ | $1.5\times$ | $1.5\times$ | $2.0\times$ (Multi-leg) |
| **Slippage Stress Multiplier** | $4.0\times$ | $2.5\times$ | $2.0\times$ | $1.5\times$ + Gap model | $2.5\times$ |
| **Latency Stress Multiplier** | $500\text{ms} \dots 1000\text{ms}$ | $200\text{ms} \dots 500\text{ms}$ | N/A (Bar Open) | N/A (Daily Close) | $500\text{ms}$ Leg drift |
| **Embargo Buffer Length** | $50$ bars | $20$ bars | $10$ bars | 2 holding horizons | $20$ bars |
| **Default OOS Partition** | $20\%$ | $20\%$ | $20\%$ | $20\%$ (or cycle-split)| $20\%$ |
