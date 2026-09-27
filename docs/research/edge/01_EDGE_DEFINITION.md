# QROS Standard: Market Edge Definition & Taxonomy
**Standard ID:** QROS-STD-EDGE-001  
**File:** `01_EDGE_DEFINITION.md`  
**Mission:** QROS-RESEARCH-001  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Formal Definition of Market Edge

In QROS, a **Market Edge** is defined as:
> **A repeatable, conditional statistical or economic advantage that persists across independent out-of-sample data regimes and generates positive expected return after factoring in all realistic execution friction, slippage, spread, and transaction costs.**

An edge is not a static property of an asset; it is a conditional distribution shift driven by identifiable market microstructure constraints, structural regulatory rules, or persistent behavioral biases of market participants.

---

## 2. Quantitative Research Taxonomy & Hierarchy of Terminology

To prevent cognitive ambiguity and premature claims of efficacy, QROS enforces a strict taxonomic hierarchy. These terms must **never** be used interchangeably:

```
[ OBSERVATION ]
       │
       ▼
   [ PATTERN ]
       │
       ▼
  [ HYPOTHESIS ]
       │
       ▼
    [ EFFECT ]
       │
       ▼
[ EDGE CANDIDATE ]
       │
       ▼
 [ CONFIRMED EDGE ]
       │
       ▼
   [ STRATEGY ]
```

### Precise Taxonomic Definitions:

1. **Observation**:
   - *Definition*: An initial empirical noticing or informal data curiosity without formal verification.
   - *Example*: "XAUUSD spreads appear to widen and price exhibits momentum around the London/New York session overlap."
2. **Pattern**:
   - *Definition*: A recurring descriptive relationship or geometric/time-series structure observed historically in price, volume, or volatility data.
   - *Note*: Patterns describe *what* happened, not *why*, and provide zero guarantee of future statistical persistence.
3. **Hypothesis**:
   - *Definition*: A formally defined, falsifiable proposition that posits a causal mechanism or conditional distributional imbalance under specified market regimes.
   - *Requirement*: Must contain a clear Null Hypothesis ($H_0$) and Alternative Hypothesis ($H_1$).
4. **Effect**:
   - *Definition*: A measurable, statistically significant anomaly or relationship documented under controlled in-sample testing.
5. **Edge Candidate**:
   - *Definition*: An effect demonstrating sufficient empirical evidence, economic rationale, positive net returns after friction, and survival across preliminary cross-validation to justify exhaustive robustness testing.
6. **Confirmed Edge**:
   - *Definition*: An edge candidate that has passed all QROS Stage 10 (Robustness) and Stage 11 (Walk-Forward / Out-of-Sample) validation gates without parameter degradation.
7. **Strategy**:
   - *Definition*: A complete, executable trading decision architecture combining one or more confirmed edges with execution logic, position sizing rules, and portfolio risk management.

---

## 3. Mandatory Non-Equivalencies ("Edge Is Not Equal to Profit")

QROS researchers and automated agents must adhere to the following foundational non-equivalencies:

| Myth / Flawed Assumption | Reality / QROS Institutional Principle |
| :--- | :--- |
| **Profitable Backtest $\neq$ Market Edge** | A backtest reflects historical curve-fit path history. An edge reflects an underlying repeatable conditional distribution. |
| **High Win Rate $\neq$ Market Edge** | A 90% win rate strategy can suffer catastrophic negative expectancy if tail losses exceed gains (e.g., martingale/grid systems). |
| **High Sharpe Ratio $\neq$ Confirmed Edge** | In-sample Sharpe ratio is vulnerable to sample selection bias, autocorrelation, and overfitting. |
| **Pattern $\neq$ Edge** | Historical patterns routinely disappear when subjected to out-of-sample data and execution friction. |
| **Correlation $\neq$ Causation** | Spurious statistical correlations abound in financial time series without an underlying economic mechanism. |
| **Statistical Significance $\neq$ Economic Significance** | A p-value $< 0.01$ with a 0.001 pip expected value is economically untradable due to bid-ask spread and broker commissions. |

---

## 4. The Edge $\rightarrow$ Module Architectural Separation

QROS maintains an absolute conceptual and architectural separation between alpha research and software execution subsystems:

```
[ Confirmed Edge ]  ──>  [ Edge Specification ]  ──>  [ Edge Module ]
 (Economic Alpha)         (Formal Math / Rules)        (Code Implementation)
```

### Separation of Concerns:
1. **Edge**:
   - The underlying economic or statistical advantage in the market.
2. **Module**:
   - The isolated, testable software unit (`src/qros/edges/`) implementing the edge logic.
3. **Strategy**:
   - The trading decision framework combining signal generation, trade timing, and risk filters.
4. **Engine**:
   - The functional platform software subsystem (e.g., Data Engine, Feature Engine, Execution Engine).
5. **Portfolio**:
   - The multi-strategy capital allocation and drawdown management layer.

> [!IMPORTANT]
> **Rule of Independence**: One edge does not equal one strategy. Multiple confirmed edges may feed a single strategy, and one strategy may be allocated across multiple portfolio buckets. No software module shall be labeled a "Strategy" if it merely encapsulates a single statistical edge.
