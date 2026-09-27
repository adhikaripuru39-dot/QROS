# QROS Standard: Edge Lifecycle Status Machine & Invalidation Standard
**Standard ID:** QROS-STD-LIFE-008  
**File:** `08_EDGE_STATUS_MACHINE.md`  
**Mission:** QROS-RESEARCH-001  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Lifecycle State Machine Architecture

In QROS, an empirical effect navigates an immutable 9-state finite state machine. Progression between states is strictly unidirectional and guarded by formal governance gates. Skipping any intermediate state is prohibited.

```
                   [ OBSERVATION ]
                          │
                          ▼ (Gate 1: Formalization)
                    [ HYPOTHESIS ]
                          │
                          ▼ (Gate 2: Empirical Backtest)
                      [ TESTED ]
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
       [ REJECTED ]               [ PROMISING ]
    (Terminal/Logged)                   │
                                        ▼ (Gate 3: Candidate Promotion)
                                 [ EDGE CANDIDATE ]
                                        │
                                        ▼ (Gate 4: Stage 10 Testing)
                              [ ROBUSTNESS PENDING ]
                                        │
                                        ▼ (Gate 5: Stage 11 OOS Validation)
                                [ CONFIRMED EDGE ]
                                        │
                                        ▼ (Gate 6: Production Staging)
                              [ ACTIVE / MONITORED ]
                                        │
                                        ▼ (Trigger: Decay / Regime Shift)
                                  [ INVALIDATED ]
```

---

## 2. State Definitions & Mandatory Transition Gates

| State | Institutional Definition | Allowed Actions | Exit Criteria / Next State |
| :--- | :--- | :--- | :--- |
| **1. OBSERVATION** | Raw empirical noticing or informal data inspection. | Data gathering, informal note taking. | Formalize into 18-field schema $\rightarrow$ `HYPOTHESIS`. |
| **2. HYPOTHESIS** | Formalized, registered research proposition (`QROS-HYP-XXXXXX`). | Code feature extraction, prepare train/val sets. | Execute In-Sample experiment $\rightarrow$ `TESTED`. |
| **3. TESTED** | Initial backtest and in-sample statistical evaluation complete. | Evaluate statistical significance & net friction. | If fails $\rightarrow$ `REJECTED`. If succeeds $\rightarrow$ `PROMISING`. |
| **4. REJECTED** | Hypothesis failed empirical or statistical criteria. | Post-mortem analysis, failure logging. | Terminal state. Retained in audit ledger permanently. |
| **5. PROMISING** | Effect shows positive net returns and preliminary statistical significance. | Refine features, prepare candidate dossier. | Pass 8-point Candidate Promotion Gate $\rightarrow$ `EDGE CANDIDATE`. |
| **6. EDGE CANDIDATE** | Official candidate with permanent ID (`QROS-EDGE-XXXXXX`). | Submit to Stage 10 Robustness Test Suite. | Authorize robustness battery $\rightarrow$ `ROBUSTNESS PENDING`. |
| **7. ROBUSTNESS PENDING** | Candidate undergoing parameter, regime, cost, and Monte Carlo stress tests. | Execute 7-dimensional perturbation tests. | Pass Stage 10 & Stage 11 Final OOS $\rightarrow$ `CONFIRMED EDGE`. |
| **8. CONFIRMED EDGE** | Validated edge passing all statistical, robustness, and OOS gates. | Authorize module development (`src/qros/edges/`). | Authorize staging $\rightarrow$ `ACTIVE / MONITORED`. |
| **9. ACTIVE / MONITORED** | Edge deployed in strategy engine under real-time telemetry. | Real-time tracking of Sharpe, spread, and decay. | If performance decays $\rightarrow$ `INVALIDATED`. |
| **10. INVALIDATED** | Edge whose statistical advantage has disappeared. | Immediate decommissioning, capital removal. | Terminal state. Post-mortem research logged. |

---

## 3. Mandatory Edge Invalidation Framework

> [!IMPORTANT]
> **No Edge Is Immortal**: Financial markets are adaptive competitive ecosystems. Every confirmed edge begins decaying the moment it is deployed. QROS strategies must incorporate pre-committed, automated invalidation triggers.

### The 6 Invalidation Triggers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   EDGE INVALIDATION CRITERIA                           │
├────────────────────────────────────────────────────────────────────────┤
│ [ ] Trigger 1: Realized Net Expectancy Decay ($\mathbb{E} \le 0$)      │
│ [ ] Trigger 2: Rolling Sharpe Ratio Collapse ($< 50\%$ of OOS Value)   │
│ [ ] Trigger 3: Maximum Drawdown Breach ($> 1.5 \times$ OOS Max DD)     │
│ [ ] Trigger 4: Execution Friction Surge (Spread/Slippage doubles)      │
│ [ ] Trigger 5: Structural Market Shift (Regulatory/Exchange rule change)│
│ [ ] Trigger 6: Ornstein-Uhlenbeck Half-Life Doubling ($\tau > 2\tau_0$) │
└────────────────────────────────────────────────────────────────────────┘
```

### Operational Invalidation Protocol:
1. When any Invalidation Trigger is breached for 3 consecutive evaluation cycles, the Edge Module is automatically set to `STATUS = INVALIDATED`.
2. The Strategy Engine immediately halts new signal generation from that module.
3. Open positions are transitioned to orderly unwind mode.
4. An Invalidation Incident Report is automatically filed in `docs/research/registry/` and the Edge Registry ledger is updated.
