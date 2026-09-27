# QROS Quantitative Standards Audit
**Mission ID:** QROS-GOV-002  
**Document:** `00_QUANTITATIVE_STANDARDS_AUDIT.md`  
**Execution Agent:** Antigravity  
**Architecture Authority:** ChatGPT  
**Date:** 2026-08-15  
**Status:** Approved Audit Report (Finalized)  

---

## 1. Executive Summary & Audit Mandate

During Mission `QROS-RESEARCH-001`, foundational standards and quantitative thresholds were established to eliminate arbitrary curve-fitting and enforce institutional discipline. However, an audit of these standards reveals that several numerical thresholds were initially framed as flat, universal constants without distinguishing between fundamentally different trading regimes and sampling frequencies.

For example, mandating a minimum sample size of $N \ge 300$ discrete trades is suitable for high-frequency M1/M5 strategies, but mathematically prohibitive for low-frequency macroeconomic regime strategies (which may generate 30–50 high-conviction structural trades across a 15-year dataset). Conversely, applying standard slippage assumptions indiscriminately to ultra-fast microstructure strategies would severely underestimate execution friction.

This audit inspects every quantitative parameter, metric, and methodology across the `QROS-RESEARCH-001` framework to classify requirements into **Layer 1 Universal Invariants** and **Layer 2 Conditional Validation Regimes**.

---

## 2. Exhaustive Quantitative Standards Audit Matrix

| Standard / Document | Metric / Parameter | Baseline Value | Underlying Assumptions | Limitations When Applied Universally | Classification & Finalization Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **01_EDGE_DEFINITION** | Net Economic Expectancy | $\mathbb{E}[\text{Net Return}] > 0$ | Friction exists on every trade. | Universally true across all markets and frequencies. | **Universal Invariant** |
| **01_EDGE_DEFINITION** | Causal vs Plausible Rationale | Causal Mechanism | Observational data makes causal proof difficult. | Causal proof cannot be strictly demanded; plausible rationale is required. | **Universal Invariant (Plausible Rationale required; ungrounded patterns get higher burden)** |
| **02_HYPOTHESIS_FRAMEWORK** | 18-Field Schema | 18 Mandatory Fields | Formal registration precedes backtesting. | Missing explicit `Research Class / Validation Profile` mapping. | **Universal Invariant (Schema Extended with Validation Profile)** |
| **04_EXPERIMENT_PROTOCOL** | Data Leakage Checklist | 8 Audit Items | Future information corrupts statistical validity. | Absolute requirement across all research. | **Universal Invariant** |
| **04_EXPERIMENT_PROTOCOL** | 4-Tier Data Split / OOS Vault | 20% EDA, 40% IS, 20% Val, 20% OOS | Chronological partitioning prevents snooping. | 20% OOS is optimal default, but specific research designs (e.g. macro cycles) may justify alternative splits. | **Universal Invariant (Protected OOS required), Conditional (20% is default baseline)** |
| **04_EXPERIMENT_PROTOCOL** | Embargo Buffer Length | 10 bars or 1 holding horizon | Autocorrelation decays over holding window. | 10 bars on M1 is 10 mins; 10 bars on D1 is 2 weeks. Must scale with holding horizon. | **Conditional (Default values in Validation Profile)** |
| **04_EXPERIMENT_PROTOCOL** | Friction Benchmarks | Spread, slippage, commission | Standard institutional FIX feed spreads. | Microstructure requires latency delay; swing requires swap financing. | **Conditional (Calibrated in Validation Profile)** |
| **05_STATISTICAL_VALIDATION** | Minimum Trade Count | $N \ge 300$ discrete trades | Central Limit Theorem asymptotic normality. | Disqualifies legitimate low-frequency macro/swing edges. | **Conditional (Initial default per Validation Regime)** |
| **05_STATISTICAL_VALIDATION** | Minimum Observation Count | $T \ge 1,000$ bar observations | Time-series stationarity testing. | D1 data has 252 bars/year; M1 generates 1,000 bars in 16 hours. | **Conditional (Initial default per Validation Regime)** |
| **05_STATISTICAL_VALIDATION** | Multiple-Testing Accounting | Trial tracking ledger ($K$) | Family-wise false positive accumulation. | Universal requirement across all research. | **Universal Invariant (Tracking & accounting universal; DSR hurdle profile-driven)** |
| **05_STATISTICAL_VALIDATION** | Deflated Sharpe Ratio (DSR) | $\text{DSR} \ge 0.95$ | Correction for $K$ family trials and non-normality. | Small-sample macro regimes require small-sample adjusted DSR ($\ge 0.90$). | **Conditional (Profile DSR Hurdle)** |
| **05_STATISTICAL_VALIDATION** | Net Profit Factor | $\text{PF} \ge 1.35$ | Net gains exceed losses with safe margin. | Trend strategies with lower win rates require different PF hurdles than scalping. | **Conditional (Initial default per Validation Regime)** |
| **06_EDGE_CANDIDATE_STANDARD** | Multi-Year Span | $\ge 3$ distinct calendar years | Sample spans multiple market environments. | Macro regimes require $\ge 12$ years (2 full economic cycles); M1 scalping requires $\ge 2$ years. | **Conditional (Calibrated by Validation Regime)** |
| **07_ROBUSTNESS_STANDARD** | Parameter Perturbation | $\pm 10\%, \pm 20\%, \pm 30\%$ | Smooth response surface around optimum. | Step size and sensitivity depend on parameter granularity. | **Conditional (Default grids in Validation Profile)** |
| **07_ROBUSTNESS_STANDARD** | Walk-Forward Efficiency (WFE) | $\text{WFE} \ge 0.60$ | Out-of-sample return retains $\ge 60\%$ of in-sample. | Realistic for momentum/trend; mean-reversion often experiences higher variance. | **Conditional (Default targets in Validation Profile)** |
| **08_EDGE_STATUS_MACHINE** | 9-State Progression | Unidirectional state transitions | Strict governance gate integrity. | Absolute requirement; no skipping allowed. | **Universal Invariant** |

---

## 3. Audit Conclusion & Key Directives

1. **Validation Regimes Over Restrictive Silos**: The 5 Research Classes are formal validation regimes specifying evaluation standards, not restrictions on what market phenomena can be researched.
2. **Validation Profile Layer**: Introduce a configuration-driven Validation Profile layer between Research Class and the downstream statistical engine.
3. **Default Calibrations**: All numerical values in the matrices are explicit initial default calibration baselines that can be overridden in pre-registered profiles when supported by documented rationale.
4. **Governance Ratification**: Formalize in `docs/DECISION_LOG.md` (ADR-014) and `docs/PROJECT_STATE.md`.
