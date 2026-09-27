# QROS Standard: Research Failure & Diagnostic Protocol
**Standard ID:** QROS-STD-FAIL-009  
**File:** `09_RESEARCH_FAILURE_PROTOCOL.md`  
**Mission:** QROS-RESEARCH-001  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Core Principle: Concluding "NO EDGE FOUND" Is a Valid Scientific Success

In QROS, scientific integrity supersedes the desire for immediate trading signals. Discovering that a market hypothesis has no statistical edge is a high-value institutional result: it prevents capital loss, eliminates false assumptions, and protects the platform from curve-fitting.

> [!CAUTION]
> **PROHIBITED FAILURE RESPONSE**:
> ❌ $\text{No Edge Found} \longrightarrow \text{Lower Acceptance Thresholds} \longrightarrow \text{Iterate Parameters} \longrightarrow \text{Overfit} \longrightarrow \text{Declare False Edge}$

---

## 2. Mandatory 8-Step Research Failure Diagnostic Workflow

When an empirical experiment produces a negative, inconclusive, or rejected outcome, researchers and automated agents must execute the following 8-step diagnostic audit before closing or pivoting the research direction:

```
                      ┌────────────────────────────────────────┐
                      │    RESEARCH FAILURE DIAGNOSTIC SUITE   │
                      ├────────────────────────────────────────┤
                      │ Step 1. Data Quality & Integrity Audit │
                      │ Step 2. Research Universe Alignment    │
                      │ Step 3. Hypothesis Quality & Specificity│
                      │ Step 4. Feature Construction Check     │
                      │ Step 5. Statistical Power & Sample Size│
                      │ Step 6. Transaction Cost Realism Audit │
                      │ Step 7. Market Regime Partitioning     │
                      │ Step 8. Next Research Vector Selection │
                      └────────────────────────────────────────┘
```

### Diagnostic Step Details:

1. **Step 1: Data Quality & Integrity Audit**:
   - Verify timestamp alignments, session time zone offsets (UTC conversion), missing tick bars, bad prints, or synthetic spread anomalies that may have corrupted the test.
2. **Step 2: Research Universe Alignment**:
   - Check whether the instrument examined matches the underlying economic mechanism (e.g., testing an interest-rate driver on an illiquid exotic FX pair instead of a major currency).
3. **Step 3: Hypothesis Quality & Specificity Check**:
   - Was the hypothesis statement too broad or ambiguous? Was the entry/exit condition truly reflecting the theoretical mechanism?
4. **Step 4: Feature Construction Check**:
   - Did feature lagging introduce look-behind attenuation? Were normalizations robust to non-stationary outliers?
5. **Step 5: Statistical Power & Sample Size**:
   - Was sample size insufficient ($N < 300$)? Is high noise obscuring a subtle signal, or is the signal-to-noise ratio (SNR) genuinely zero?
6. **Step 6: Transaction Cost Realism Audit**:
   - Did the gross signal work, but fail strictly due to punitive retail-tier fee assumptions? Would execution improvements (e.g. limit orders vs. market orders) alter the viability?
7. **Step 7: Market Regime Partitioning**:
   - Did the effect get masked by evaluating across full market cycles when the mechanism is strictly active during specific volatility or session regimes?
8. **Step 8: Determine Next Research Direction**:
   - Formally document the root cause of the negative result. Archive the failure record in the global registry and formulate a new distinct hypothesis.

---

## 3. Mandatory Failure Post-Mortem Template

Every rejected hypothesis must conclude with a documented post-mortem entry:

```markdown
# QROS Research Post-Mortem: QROS-HYP-XXXXXX

- **Hypothesis ID:** QROS-HYP-XXXXXX
- **Experiment ID:** QROS-EXP-XXXXXX
- **Termination Date:** YYYY-MM-DD
- **Final Status:** `REJECTED`

### 1. Rejection Summary
[Summary of why the hypothesis failed to achieve statistical or economic thresholds]

### 2. Empirical Outcome
- **In-Sample Sharpe Ratio:** [Value]
- **Net Expectancy After Costs:** [Value]
- **Deflated Sharpe Ratio (DSR):** [Value]
- **Key Failure Gate:** [e.g., Gate 4: Negative Expectancy after Slippage]

### 3. Diagnostic Audit Findings
- **Data Quality:** [Clean / Flawed]
- **Economic Mechanism:** [Invalidated / Non-existent in modern market structure]
- **Regime Sensitivity:** [Failed across all regimes / Inactive]

### 4. Institutional Lessons Learned
[What does this result teach QROS about market behavior, liquidity, or feature modeling?]

### 5. Architectural Action
- [x] Permanently recorded in Global Experiment Ledger.
- [x] Parameter configuration flagged to prevent future redundant testing.
```
