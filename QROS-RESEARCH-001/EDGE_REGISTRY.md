# QROS Edge Registry Specification & Master Catalog
**Standard ID:** QROS-REG-EDGE-010  
**File:** `EDGE_REGISTRY.md`  
**Mission:** QROS-RESEARCH-001  
**Status:** Mandatory Institutional Standard & Master Ledger  
**Authority:** QROS Architecture Authority  

---

## 1. Registry Architecture & Governance

The **QROS Edge Registry** is the central institutional ledger of all alpha candidates and confirmed market edges. No trading strategy shall be coded in `src/qros/edges/` or staged for execution unless it is officially registered in this catalog with an active status.

Every entry in the registry is assigned an immutable identifier formatted as:

$$\text{Format: } \mathbf{QROS\text{-}EDGE\text{-}XXXXXX}$$

---

## 2. Mandatory 21-Field Edge Registry Schema

Every registered edge record must contain the following 21 metadata fields:

| Field # | Field Name | Description & Specification |
| :--- | :--- | :--- |
| **1** | `Edge ID` | Unique permanent identifier (`QROS-EDGE-XXXXXX`). |
| **2** | `Hypothesis ID` | Source hypothesis (`QROS-HYP-XXXXXX`). |
| **3** | `Market` | Asset class and specific instrument (e.g., `XAUUSD`). |
| **4** | `Timeframe` | Primary frequency (`M1`, `M5`, `H1`, `D1`). |
| **5** | `Definition` | Formal mathematical entry/exit state rules. |
| **6** | `Mechanism` | Causal economic/microstructure/behavioral driver. |
| **7** | `Dataset Lineage` | Dataset ID, version, and cryptographic hash (`SHA-256`). |
| **8** | `Research History` | Experiment IDs (`QROS-EXP-XXXXXX`) and Git commit hash. |
| **9** | `Sample Size` | Total discrete trade observations ($N$). |
| **10** | `Gross Result` | Gross Profit Factor, Gross Sharpe, Gross Expectancy. |
| **11** | `Net Result` | Net Profit Factor, Net Sharpe, Net Expectancy after all costs. |
| **12** | `Costs Applied` | Spread, slippage, commission, and swap benchmarks used. |
| **13** | `Statistical Metrics` | $t$-statistic, Deflated Sharpe Ratio (DSR), 95% Bootstrap CI. |
| **14** | `OOS Results` | Final Tier 4 Out-of-Sample Sharpe, Return, and Drawdown. |
| **15** | `Robustness Index` | Parameter plateau stability ($\pm 20\%$), WFE ratio ($\ge 0.60$). |
| **16** | `Regime Bounds` | Operating volatility regimes and session boundaries. |
| **17** | `Status` | `CANDIDATE`, `CONFIRMED`, `ACTIVE`, `INVALIDATED`, `RETIRED`. |
| **18** | `Version` | Semantic version string (e.g., `v1.0.0`). |
| **19** | `Creation Date` | ISO-8601 timestamp of candidate creation. |
| **20** | `Last Validation` | ISO-8601 timestamp of most recent validation audit. |
| **21** | `Invalidation Criteria` | Pre-committed degradation thresholds for decommissioning. |

---

## 3. Master Edge Registry Ledger

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          QROS MASTER EDGE REGISTRY                                               │
├──────────────────┬─────────────────┬──────────┬───────────┬─────────────┬─────────────┬───────────┬──────────────┤
│ Edge ID          │ Hypothesis ID   │ Asset    │ Frequency │ Net Sharpe  │ DSR Score   │ Status    │ Last Audit   │
├──────────────────┼─────────────────┼──────────┼───────────┼─────────────┼─────────────┼───────────┼──────────────┤
│ QROS-EDGE-000000 │ QROS-HYP-000000 │ NULL     │ NULL      │ 0.00        │ 0.00        │ BENCHMARK │ 2026-08-14   │
│ [CATALOG OPEN]   │ --              │ --       │ --        │ --          │ --          │ --        │ --           │
└──────────────────┴─────────────────┴──────────┴───────────┴─────────────┴─────────────┴───────────┴──────────────┘
```
*(Note: As of Mission QROS-RESEARCH-001 Baseline, research has not yet produced a confirmed market edge. The registry is initialized in readiness for empirical ingestion under Stage 5 through Stage 11.)*

---

## 4. Edge Registration & Modification Governance

1. **New Registration**: Authorized only upon passing Stage 8 Statistical Verification and Gate 3 (`PROMISING` $\rightarrow$ `EDGE CANDIDATE`).
2. **Confirmation Update**: Status promoted to `CONFIRMED` only after successful completion of Stage 10 Robustness and Stage 11 Walk-Forward gates.
3. **Invalidation**: Triggered immediately upon breach of pre-committed invalidation thresholds.
4. **Audit Trail**: Every update to `EDGE_REGISTRY.md` must be committed to Git with reference to the approving ADR or experiment dossier.
