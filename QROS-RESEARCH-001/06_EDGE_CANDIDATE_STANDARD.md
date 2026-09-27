# QROS Standard: Edge Candidate Promotion Standard
**Standard ID:** QROS-STD-CAND-006  
**File:** `06_EDGE_CANDIDATE_STANDARD.md`  
**Mission:** QROS-RESEARCH-001 (Amended by QROS-GOV-002)  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Objective & Gate Definition

An **Edge Candidate** represents a significant milestone in the QROS research pipeline: an empirical effect that has demonstrated sufficient statistical rigor, economic justification, and resistance to transaction costs to justify intensive Stage 10 (Robustness) and Stage 11 (Walk-Forward) stress testing.

> [!WARNING]
> **Candidate $\neq$ Confirmed Edge**: An Edge Candidate is strictly an unconfirmed hypothesis under deep evaluation. It is forbidden to deploy capital, construct production trading strategies, or make external efficacy claims based on Candidate status.

---

## 2. Mandatory 8-Point Candidate Promotion Gate

An effect shall **NOT** be promoted to Candidate status unless it unconditionally passes all 8 gate criteria:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   EDGE CANDIDATE PROMOTION GATES                       │
├────────────────────────────────────────────────────────────────────────┤
│ [ ] Gate 1: Unambiguous Mathematical Specification                     │
│ [ ] Gate 2: Full End-to-End Reproducibility                            │
│ [ ] Gate 3: Class-Calibrated Sample Power ($N$ & $T$)                  │
│ [ ] Gate 4: Positive Net Economic Expectancy After Friction            │
│ [ ] Gate 5: Plausible Microstructure / Behavioral Mechanism            │
│ [ ] Gate 6: Robust Statistical Thresholds ($t > 3.0$, DSR $\ge 0.95$)   │
│ [ ] Gate 7: Verified Zero Data Leakage Audit                           │
│ [ ] Gate 8: Immutable Lineage & Experiment Record Traceability         │
└────────────────────────────────────────────────────────────────────────┘
```

### Detailed Evaluation Rules:

1. **Unambiguous Specification (Gate 1)**:
   - Complete formal rules for signal evaluation, parameter vectors, execution assumptions, and market regime filters without vague terms.
2. **Reproducibility (Gate 2)**:
   - An independent agent running the identical dataset version (`SHA-256`) and configuration must generate identical performance metrics within floating-point tolerance ($10^{-6}$).
3. **Sample Power (Gate 3)**:
   - Must satisfy the minimum discrete trade count ($N$), observation count ($T$), and calendar span specified for its declared **Research Class** (per `02_RESEARCH_CLASS_SPECIFICATION.md`):
     - `CLASS-I (HF-MICRO)`: $N \ge 1,000$, $T \ge 50,000$, $\ge 2$ years.
     - `CLASS-II (INTRADAY-MOM)`: $N \ge 400$, $T \ge 15,000$, $\ge 3$ years.
     - `CLASS-III (SWING-STATARB)`: $N \ge 150$, $T \ge 5,000$, $\ge 5$ years.
     - `CLASS-IV (MACRO-REGIME)`: $N \ge 40$, $T \ge 3,000$, $\ge 12$ years (2 economic cycles).
     - `CLASS-V (CROSS-FACTOR)`: $N \ge 500$ pooled, $T \ge 10,000$, $\ge 5$ years.
4. **Net Economic Expectancy (Gate 4)**:
   - Must achieve class target Net Profit Factor ($\ge 1.30 \dots \ge 1.50$) and positive net expectancy after applying class-specific spread multipliers, institutional slippage, and round-turn commissions.
5. **Economic Mechanism (Gate 5)**:
   - Must be supported by an established market dynamic:
     - *Structural*: Exchange rules, fixing windows, ETF arbitrage boundaries.
     - *Behavioral*: Disposition effect, retail herd momentum, weekend gap aversion.
     - *Microstructure*: Order book inventory rebalancing, liquidity provider spread asymmetry.
6. **Statistical Hurdles (Gate 6)**:
   - Asymptotic $t$-statistic $> 3.0$ on net returns (or Panel $t > 3.5$ for Class V).
   - Deflated Sharpe Ratio $\text{DSR} \ge 0.95$ (or small-sample adjusted $\text{DSR} \ge 0.90$ for Class IV) adjusting for total family trials ($K$).
   - 95% Stationary Bootstrap Confidence Interval lower bound $> 0.0$.
7. **Zero Leakage (Gate 7)**:
   - Verified compliance with all 8 items of `04_EXPERIMENT_PROTOCOL.md` Section 3.
8. **Lineage Traceability (Gate 8)**:
   - Linked to Git commit hash, dataset manifest, declared Research Class, and trial count ledger.

---

## 3. Candidate Promotion Protocol & Dossier

Upon passing all 8 gates:
1. The hypothesis status transitions from `PROMISING` to `EDGE CANDIDATE`.
2. A formal **Candidate Dossier** is generated and entered into the `EDGE_REGISTRY`.
3. The candidate is assigned an official Edge Identifier (`QROS-EDGE-XXXXXX`).
4. Stage 10 Robustness Testing is formally authorized.
