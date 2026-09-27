# QROS Statistical Core & Dataset Infrastructure Architecture & API Reference
**Standard Reference:** QROS-ARCH-STAT-002  
**Mission:** QROS-RESEARCH-002  
**Version:** 0.2.0  
**Author:** QROS Quantitative Architecture Team  
**Status:** Canonical Living Specification  

---

## 1. Architectural Overview

The **QROS Statistical Core & Dataset Infrastructure** provides the reusable, non-strategy-specific scientific instruments required for institutional quantitative research. It implements the dual-layer governance model formalized in `QROS-GOV-002`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          QROS RESEARCH ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
           ┌──────────────────────────┴──────────────────────────┐
           ▼                                                     ▼
┌────────────────────────────────────┐        ┌───────────────────────────────┐
│     DATASET INFRASTRUCTURE         │        │    SCHEMAS & GOVERNANCE       │
│  - OHLCV Validation & Cleansing    │        │  - 18-Field Hypothesis Schema │
│  - SHA-256 Dataset Hashing         │        │  - 19-Field Experiment Schema │
│  - 4-Tier Chronological Partition  │        │  - ValidationProfile Model    │
│  - Purging & Embargo Buffers       │        │  - Statistical Results Schema │
└────────────────────────────────────┘        └───────────────────────────────┘
           │                                                     │
           └──────────────────────────┬──────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       STATISTICAL CALCULATION ENGINE                        │
│  - Higher Moments (Skewness, Kurtosis, VaR, CVaR, Effective Sample Size)    │
│  - Deflated Sharpe Ratio (DSR) & Probabilistic Sharpe Ratio (PSR)           │
│  - Stationary Block Bootstrap (Politis & Romano, 1994)                      │
│  - Multiple-Testing Adjustments (Benjamini-Hochberg FDR)                    │
│  - Calibrated Transaction Cost & Friction Models                            │
│  - Global Experimentation Trial Ledger ($K$) & Cryptographic Lineage        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. API & Component Reference

### 2.1 Schemas & Validation Profiles (`src/qros/schemas/`)

#### `ValidationProfile`
A declarative container that binds a Research Class (`CLASS-I` through `CLASS-V`) to quantitative evaluation hurdles:
```python
from qros.schemas import get_default_profile, ValidationProfile

# Load canonical default calibration for Intraday Momentum
profile = get_default_profile("CLASS-II")
print(profile.min_trades)  # 400
print(profile.target_sharpe)  # 1.40
print(profile.dsr_hurdle)  # 0.95
```

#### `HypothesisRecord`
Enforces the mandatory 18-field hypothesis schema, validates identifier syntax (`QROS-HYP-XXXXXX`), and verifies the 6 Quality Gates:
```python
from qros.schemas import HypothesisRecord

hyp = HypothesisRecord(
    hypothesis_id="QROS-HYP-000001",
    market="Commodities",
    asset="XAUUSD",
    timeframe="M5",
    research_class="CLASS-II",
    market_condition="London Open Volatility Expansion",
    observation="Strong momentum drift after initial London breakout.",
    hypothesis_statement="M5 momentum breakout during London open yields positive drift over 12 bars.",
    plausible_rationale="London fixing and institutional liquidity participation creates session trend continuation.",
    entry_condition="Close > RollingHigh(20)",
    exit_condition="TimeStop(12) or VolatilityStop(2.0*ATR)",
    holding_period="12 bars (1 hour)",
    expected_effect="Forward mean return > 0.20 sigma",
    null_hypothesis="H_0: Mean forward return <= 0.0",
    alternative_hypothesis="H_1: Mean forward return > 0.0",
    required_data="XAUUSD M5 Tick-aggregated OHLCV",
    potential_confounders="US/UK Bank Holidays, NFP releases",
    transaction_cost_assumptions="20 pts spread, 8 pts slippage",
)
quality_gates = hyp.validate_quality_standard()
```

---

### 2.2 Dataset Infrastructure (`src/qros/data/`)

#### `validate_ohlcv_dataframe(df, ...)`
Audits financial time-series for UTC timezone alignment, monotonic index ordering, missing bars, NaN/infinite values, and mathematical price consistency ($High \ge \max(Open, Close, Low)$). Computes deterministic SHA-256 hash.

#### `DataSplitter(eda_pct=0.20, train_pct=0.40, val_pct=0.20, oos_pct=0.20)`
Partitions datasets into 4 chronological tiers:
- **Tier 1 (EDA / Discovery)**: 20%
- **Tier 2 (Train / In-Sample)**: 40%
- **Tier 3 (Validation / Tuning)**: 20%
- **Tier 4 (Protected OOS Vault)**: 20% (Raises `ProtectedOOSViolationError` if accessed without formal governance unlock token).

#### `purge_overlapping_labels` & `compute_embargo_cutoff`
Prevents label leakage from overlapping multi-bar trades and eliminates post-test serial autocorrelation.

---

### 2.3 Statistical Engine (`src/qros/stats/`)

#### `calculate_dsr(observed_sharpe, trial_count_k, sample_length_t, skewness, kurtosis, dsr_hurdle=0.95)`
Implements Bailey & López de Prado (2014) Deflated Sharpe Ratio:
$$\text{DSR} = \Phi\left(\frac{\widehat{\text{SR}} - \text{SR}^*}{\sqrt{\frac{1 - \widehat{\gamma}_3 \widehat{\text{SR}} + \frac{\widehat{\gamma}_4 - 1}{4}\widehat{\text{SR}}^2}{T - 1}}}\right)$$
where $\text{SR}^*$ is the expected maximum Sharpe under $K$ trials.

#### `StationaryBlockBootstrap(expected_block_length=10.0)`
Politis & Romano (1994) stationary bootstrap with geometric block lengths:
$$\mathbb{P}(L = k) = (1 - p)^{k-1} p, \quad p = \frac{1}{\text{expected\_block\_length}}$$
Computes 95% non-parametric confidence intervals for Sharpe Ratio over $B \ge 2,000$ iterations.

#### `calculate_effective_sample_size(returns, max_lags=20)`
Calculates autocorrelation-adjusted discrete sample power $N_{\text{eff}}$:
$$N_{\text{eff}} = \frac{N}{1 + 2 \sum_{k=1}^{L} \rho(k)}$$

#### `benjamini_hochberg(p_values, fdr_q=0.05)`
Controls False Discovery Rate (FDR) across multiple hypothesis screening iterations.

---

### 2.4 Tracking & Provenance (`src/qros/tracking/`)

#### `GlobalTrialLedger`
Thread-safe persistent ledger tracking all trial variations ($K$), hypothesis counts, and experiment outcomes across research lifetime (`docs/research/tracking/TRIAL_LEDGER.json`).

#### `capture_lineage(dataset_sha256, random_seed, validation_profile_name)`
Captures Git commit hash, working tree dirty flag, Python version, platform, and dataset SHA-256 hash.

---

### 2.5 Pipeline & Cost Modeling (`src/qros/pipeline/`)

#### `TransactionCostModel(base_config, profile)`
Calculates nominal and stress-multiplied spread, fixed commission, slippage stress, swap financing, and execution latency drift penalties.

#### `evaluate_statistical_profile(...)`
Unified evaluation orchestrator executing the full battery of statistical tests and outputting an auditable `StatisticalResult`.
