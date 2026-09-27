# QROS Universal vs. Conditional Requirements Framework
**Standard ID:** QROS-GOV-FRAME-002  
**Document:** `01_UNIVERSAL_VS_CONDITIONAL_FRAMEWORK.md`  
**Mission:** QROS-GOV-002 (Finalized)  
**Status:** Mandatory Institutional Governance Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Principle of Architectural Invariance

To maintain institutional integrity while accommodating diverse quantitative trading domains, QROS divides all research rules into two distinct ontological categories:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      QROS DUAL-LAYER GOVERNANCE SYSTEM                      │
├──────────────────────────────────────┬──────────────────────────────────────┤
│       LAYER 1: UNIVERSAL INVARIANTS  │     LAYER 2: CONDITIONAL STANDARDS   │
│  (Absolute, Non-Negotiable, Global)  │ (Class-Specific, Regime-Calibrated)  │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • Zero Data Leakage Protocol         │ • Initial Min. Discrete Trades ($N$) │
│ • Hypothesis Pre-Registration        │ • Initial Min. Observations ($T$)    │
│ • Net Expectancy After All Friction  │ • Expected Holding Horizon           │
│ • Universal Multiple-Testing Track   │ • Target Profit Factor & Win Rate    │
│ • Mandatory Protected Final OOS Set  │ • Parameter Perturbation Grids       │
│ • Plausible Documented Rationale     │ • Walk-Forward Efficiency Targets    │
│ • 9-State Unidirectional Lifecycle   │ • Cross-Asset Resonance Tests        │
│ • Cryptographic Lineage & Versioning │ • Execution Friction Stress Models   │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Layer 1: Universal Invariants (Global & Uncompromising)

Universal Invariants are structural axioms. They apply **identically to every hypothesis, experiment, model, and edge candidate** regardless of timeframe, asset class, or strategy style.

### The 8 Universal Invariants:

1. **Strict Data Leakage Elimination**:
   - Every experiment must pass the 8-point data leakage audit (no look-ahead, explicit feature lagging $t-1$, strictly in-sample normalization fitting, UTC timestamps, trade label purging/embargoing).
2. **Mandatory Hypothesis Pre-Registration**:
   - No empirical code or backtest execution is authorized without an approved hypothesis registered in `docs/research/` under `QROS-HYP-XXXXXX`.
3. **True Net Economic Expectancy**:
   - An edge must demonstrate positive expected return **after deducting all realistic institutional spread, commission, slippage, and rollover financing costs**. Gross profitability is disqualified as evidence.
4. **Universal Multiple-Testing Accounting & Trial Tracking**:
   - The total number of parameter variations, feature combinations, and hypothesis trials ($K$) must be permanently recorded in the global experimentation ledger and accounted for in multiple-testing adjustments. *(Note: While multiple-testing tracking is universal, specific Deflated Sharpe Ratio (DSR) threshold hurdles are determined by the applicable Validation Profile).*
5. **Mandatory Protected Final Out-of-Sample (OOS) Dataset**:
   - A protected final OOS partition must remain unexamined throughout the discovery and tuning phases, accessed strictly once at the final gate. A 20% allocation serves as the default baseline unless the specific research design explicitly documents and justifies an alternative partitioning. Iterative optimization on the protected partition results in immediate disqualification.
6. **Plausible, Documented Economic / Behavioral / Structural Rationale**:
   - Every hypothesis must document a plausible theoretical mechanism (e.g., behavioral bias, structural/regulatory constraint, order book liquidity imbalance, or macro flow driver). Causal mathematical proof is not universally required given the observational nature of market data; however, statistical anomalies lacking documented theoretical rationale receive an elevated validation burden (e.g., stricter bootstrap confidence intervals and broader cross-asset stability hurdles).
7. **9-State Finite State Machine Lifecycle**:
   - All effects must advance through the full lifecycle sequence (`OBSERVATION` $\rightarrow$ `HYPOTHESIS` $\rightarrow$ `TESTED` $\rightarrow$ `PROMISING` $\rightarrow$ `EDGE CANDIDATE` $\rightarrow$ `ROBUSTNESS PENDING` $\rightarrow$ `CONFIRMED EDGE` $\rightarrow$ `ACTIVE` $\rightarrow$ `INVALIDATED`). Skipping gates is forbidden.
8. **Cryptographic Lineage & Reproducibility**:
   - Every experiment record must link to an immutable Git commit hash, dataset SHA-256 hash, and seed configuration, ensuring $100\%$ byte-for-byte reproducibility.

---

## 3. Layer 2: Conditional Requirements (Validation Regimes)

Conditional Requirements are quantitative criteria whose mathematical and statistical validity depends directly on the temporal frequency, holding period, and market dynamics of the research.

### Research Classes as Validation Regimes:
The 5 Research Classes (`CLASS-I` through `CLASS-V`) represent **validation regimes**—sampling and evaluation environments tailored to specific market dynamics—rather than restrictive boundaries on the types of market phenomena QROS may research. Any valid market phenomenon can be researched provided it is evaluated under the appropriate validation regime.

### Configuration-Driven Validation Profiles:
To bridge abstract Research Classes and the downstream analytical engine, QROS introduces the concept of a **Validation Profile**:
* A **Validation Profile** is a declarative configuration object that binds specific quantitative hurdles (sample sizes, observation minimums, DSR hurdles, perturbation ranges, and friction multipliers) to a hypothesis or experiment.
* All quantitative matrix parameters serve as **initial/default calibration values**, which may be fine-tuned or overridden in a specific validation profile when scientifically justified and pre-registered in the hypothesis dossier.
