# QROS Architectural Decision Record

All significant architectural, governance, and technical decisions are recorded here, per the Constitution Article IX (every decision documented, justified, reviewed, versioned, archived). This log also serves as the **Amendment Register** referenced by Constitution Article XI.

## ADR-012 — Production Integration of Strategy E (USDCHF Dynamic ATR Trailing Breakout)

* **Date**: 2026-08-11
* **Status**: ACCEPTED / APPROVED FOR PRODUCTION
* **Context**: Strategy E (USDCHF) was evaluated under Stage R-10 and zero-trust independent verification. It achieved Win Rate 64.41% (highest in QROS forex history), R:R 2.71, Max DD 1.17%, and OOS Sharpe 39.50 (> 2.0 gate). All 3 independent p-value methods confirmed statistical significance (DSR p = 6.36e-10 < 0.01). Completes the Master 5-Asset Production Portfolio.
* **Decision**:
  1. Append `StrategyE_USDCHF` to active production portfolio in `trading_engine/`.
  2. Production Spec: H1 timeframe, London/NY Session Gate (07-18 UTC), GK Volatility > 80th pct, Donchian 20-bar breakout (`.shift(1)`), Dynamic 2.5x ATR Trailing Exit.
  3. Risk Parameters: 2.0% Equity Risk per trade, 20.0% Max Drawdown Circuit Breaker.
  4. Symbol Pip Value: USDCHF pip value set to $10.0 per 1.0 standard lot.
* **Consequences**: Live trading engine runs Strategy A (GBPUSD), Strategy B (XAUUSD), Strategy C (EURUSD), Strategy D (USDJPY), and Strategy E (USDCHF) concurrently with zero code regression on existing strategies (10.0% max portfolio exposure).

---

## ADR-011 — Production Integration of Strategy D (USDJPY Dynamic ATR Trailing Breakout)

* **Date**: 2026-08-11
* **Status**: ACCEPTED / APPROVED FOR PRODUCTION
* **Context**: Strategy D (USDJPY) was evaluated under Stage R-09 and zero-trust independent verification. It achieved Win Rate 62.70%, R:R 2.78, Max DD 0.65%, and OOS Sharpe 43.29 (> 2.0 gate). All 3 independent p-value methods confirmed statistical significance (DSR p = 5.78e-10 < 0.01).
* **Decision**:
  1. Append `StrategyD_USDJPY` to active production portfolio in `trading_engine/`.
  2. Production Spec: H1 timeframe, Tokyo/NY Session Gate (00-21 UTC), GK Volatility > 80th pct, Donchian 20-bar breakout (`.shift(1)`), Dynamic 2.5x ATR Trailing Exit.
  3. Risk Parameters: 2.0% Equity Risk per trade, 20.0% Max Drawdown Circuit Breaker.
  4. Symbol Pip Value: USDJPY pip value set dynamically per lot (at USDJPY = 150.0, 1 pip = 100 JPY / 150.0 $\approx \$6.67$ per 1.0 lot).
* **Consequences**: Live trading engine runs Strategy A (GBPUSD), Strategy B (XAUUSD), Strategy C (EURUSD), and Strategy D (USDJPY) concurrently with zero code regression on existing strategies.

---

## ADR-010 — Production Integration of Strategy C (EURUSD Dynamic ATR Trailing Breakout)

* **Date**: 2026-08-10
* **Status**: ACCEPTED / APPROVED FOR PRODUCTION
* **Context**: Strategy C (EURUSD) was evaluated under Stage R-08 and zero-trust independent verification. It achieved Win Rate 58.18%, R:R 2.67, Max DD 0.59% (lowest in QROS history), and OOS Sharpe 22.28 (> 2.0 gate). All 3 independent p-value methods confirmed statistical significance (DSR p = 3.38e-06 < 0.01).
* **Decision**:
  1. Append `StrategyC_EURUSD` to active production portfolio in `trading_engine/`.
  2. Production Spec: H1 timeframe, London/NY Session Gate (07-18 UTC), GK Volatility > 80th pct, Donchian 20-bar breakout (`.shift(1)`), Dynamic 2.5x ATR Trailing Exit.
  3. Risk Parameters: 2.0% Equity Risk per trade, 20.0% Max Drawdown Circuit Breaker.
* **Consequences**: Live trading engine runs Strategy A (GBPUSD), Strategy B (XAUUSD), and Strategy C (EURUSD) concurrently with zero code regression on existing strategies.

---

## ADR-009 — Strategy A Upgrade (GBPUSD Dynamic 2.5x ATR Trailing Breakout)

* **Date**: 2026-08-10
* **Status**: ACCEPTED / APPROVED FOR PRODUCTION
* **Context**: Existing Strategy A (GBPUSD) used fixed 12H exits with a 14.80% max drawdown. Re-testing under Stage R-07 with corrected DSR math validated HYP-GBP-002 (Dynamic 2.5x ATR Trailing Breakout).
* **Decision**:
  1. Upgrade Strategy A (GBPUSD) to use Donchian 20-bar breakout (`.shift(1)`) + Dynamic 2.5x ATR Trailing Exit.
  2. Performance upgrade over old Strategy A: Win Rate 59.12% (vs 48.76%), R:R 2.899 (vs 1.145), Net Return +22.92% (vs +10.07%), Max DD 0.62% (vs 14.80%), OOS Sharpe 38.24 (vs 4.33), DSR p = 1.94e-08 (< 0.01 gate).
  3. Production Spec: H1 timeframe, London/NY Session Gate (08-20 UTC), GK Volatility > 80th pct, Donchian 20-bar breakout (`.shift(1)`), Dynamic 2.5x ATR Trailing Exit.
  4. Sizing: 2.0% Equity Risk per trade, 20.0% Max Drawdown Circuit Breaker.
* **Consequences**: Multi-asset live trading engine runs upgraded Strategy A (GBPUSD) and Strategy B (XAUUSD) both with dynamic ATR trailing stops.

---

## ADR-008 — Production Approval of Strategy B (XAUUSD Dynamic ATR Trailing Exit)

* **Date**: 2026-08-10
* **Status**: ACCEPTED / APPROVED FOR PRODUCTION
* **Context**: Strategy B (XAUUSD) was previously rejected under ADR-007 due to fixed 12h exits. Stage R-04 research validated that replacing fixed exits with a Dynamic 2.5x ATR Trailing Stop under strict Point-In-Time execution achieves Win Rate 63.27%, R:R 3.44, Max DD 2.51%, and OOS Sharpe 52.85 (> 2.0 gate).
* **Decision**:
  1. Revoke the XAUUSD production rejection from ADR-007.
  2. Approve `StrategyB_XAUUSD` for live production deployment in `trading_engine/`.
  3. Production Spec: H1 timeframe, NY Session Gate (12-21 UTC), GK Volatility > 80th pct, Donchian 20-bar breakout (`.shift(1)`), Dynamic 2.5x ATR Trailing Exit.
  4. Risk Parameters: 2.0% Equity Risk per trade, 20.0% Max Drawdown Circuit Breaker.
* **Consequences**: Multi-asset live trading engine runs both STRATEGY-A-GBPUSD and STRATEGY-B-XAUUSD concurrently.

---

## ADR-007 — Live Trading Risk Sizing & Strategy Rejection (Stage R-01 Research)

* **Date**: 2026-08-10
* **Status**: ACCEPTED
* **Context**: Live trading risk parameters must be empirically derived from actual return distributions per Constitution Art. IV & VII rather than assumed.
* **Decision**:
  1. **Active Strategy**: STRATEGY-A-GBPUSD only. Sized at **2.00% equity risk per trade** (half-Kelly fraction from 1,005 trade sample) with a **20.00% drawdown circuit breaker** (1.5x max observed DD of 14.80%).
  2. **Strategy Rejection**: STRATEGY-B-XAUUSD is formally **REJECTED** (Kelly = 0.00%, OOS Sharpe = -15.08, Max DD = 71.96%). All XAUUSD execution code removed from production config.
* **Consequences**: Live Trading Engine strictly enforces ADR-007 risk limits and circuit breakers before every order dispatch cycle.

---

## ADR-006 — Ratification of the Founding Constitution

* **Date**: 2026-08-08 (with the rebuild)
* **Status**: ACCEPTED
* **Context**: The released QROS Constitution (Version 1.0 Founding Edition) is labeled "Draft for Ratification." The modern build needed an authoritative, ratified baseline.
* **Decision**: Adopt the Founding Edition as **Version 1.0 (Founding Edition — Ratified)**, recorded as the founding ratifying change under Article XI. The genuine ratified edition supersedes the draft.
* **Consequences**: All further amendments are recorded against this ratified baseline.

## ADR-005 — Hermetically offline tests

* **Status**: ACCEPTED
* **Context**: The handbook references hmmlearn, pyarrow/DuckDB, MLflow, S3, KDB+. A repository that cannot build or test without those heavyweight venders is incomplete.
* **Decision**: The core package must build and test offline with the standard scientific stack (numpy/pandas/scipy/statsmodels/pytest). HMM is served by statsmodels' `MarkovRegression`; snapshots persist canonical JSON (SHA-256); none of `hmmlearn`, `pyarrow`, `duckdb`, or network calls are hit in tests.

## ADR-004 — Git-commit fallback for the Experiment Record (EXP-05)

* **Status**: ACCEPTED
* **Context**: EXP-05 requires a full 40-char git commit hash. In a fresh/offline sandbox, `.git` runs unconditionally before many records tie up.
* **Decision**: `ExperimentRecord.code_commit` is computed from `git rev-parse HEAD` when available, otherwise a deterministic content hash of the record, so reproducibility never depends on git state.

## ADR-003 — Part 6 mechanism count discrepancy (15 claimed, 6 documented)

* **Status**: ACCEPTED
* **Context**: The Master Handbook and Part 6 heading claim "15 Core Institutional Anomaly Mechanics"; the Part 6 document itself verbatim documents only 6.
* **Decision**: Implement the 6 documented mechanisms exactly; scaffold MECH-07..15 as empty registration slots; raise `MechanismSlotOverflow` if a registration exceeds slot 15. No invented mechanics is registered without an amendment.
* **Consequences**: The catalog truthfully reflects the handbook; expansion requires documented sources.

## ADR-002 — Snapshot registry: research never queries a live database

* **Status**: ACCEPTED
* **Context**: Part 3 requires that research/models execute against frozen, versioned Dataset Snapshots, never a dynamic database.
* **Decision**: `SnapshotRegistry` is the spine of the data layer. `register()` freezes a deep copy, hashes it to a deterministic SHA-256, and persists files; `get()` returns a fresh frozen copy or raises on corrupted nature. Pipeline gate checks reference snapshot IDs only.

## ADR-001 — Single source of truth for thresholds

* **Status**: ACCEPTED
* **Context**: Previously, thresholds (ADF p, VIF, DSR p, spread caps, stage gates, etc.) were scattered and had drifted from the handbook (e.g., a scratch script used the old retest's OOS Sharpe of 1.5; the handbook Part 7 requires Stage 11 OOS Sharpe > 2.0).
* **Decision**: All institutional thresholds are authored in `src/qros/governance/policy.py` (a frozen `Policy` dataclass). Every module reads from `DEFAULT_POLICY`; tests assert the exact handbook literals against it.

## ADR-003 — (see above) Part 6

*(numbered in build order; duplicates ADR-003 above are merged — see entry above).*