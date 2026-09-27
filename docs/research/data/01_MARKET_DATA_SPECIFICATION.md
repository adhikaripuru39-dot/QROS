# QROS Market Data Specification: Primary Asset (XAUUSD)
**Standard Identifier:** QROS-STD-DATA-004  
**Mission:** QROS-RESEARCH-004  
**Primary Research Asset:** XAUUSD (Spot Gold vs. US Dollar)  
**Governing Authority:** Stage 3 Data Quality Charter & Stage 2 Data Foundation  
**Status:** Approved Canonical Standard  

---

## 1. Primary Asset Overview & Specifications

Spot Gold priced in US Dollars (`XAUUSD` / `GOLD`) is the primary reference asset for the initial QROS quantitative research pipeline.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          XAUUSD INSTRUMENT SPECIFICATIONS                   │
├─────────────────────────┬───────────────────────────────────────────────────┤
│ Base / Quote            │ Gold (1 Troy Ounce) / US Dollar (USD)             │
│ Standard Contract Size  │ 100 Troy Ounces                                   │
│ Digits / Precision      │ 2 Decimal Places ($0.01)                          │
│ Tick Size / Point Size  │ 0.01 USD / Point                                  │
│ Pip Definition          │ 0.10 USD (10 Points = 1 Pip)                      │
│ Typical Nominal Spread  │ 15 – 25 Points ($0.15 – $0.25 / oz)               │
│ Daily Settlement Roll   │ 17:00 NY Time (22:00 UTC / 21:00 UTC DST)         │
│ Trading Sessions        │ 24/5 (Sun 22:00 UTC -> Fri 21:00 UTC)             │
│ Daily Maintenance Break │ 21:00 UTC -> 22:00 UTC (1-Hour Session Roll)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Canonical Data Schema & Types

Every financial time-series ingested into QROS must conform to the following Apache Arrow-compatible schema:

| Column Name | Data Type | Nullable | Required | Definition & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` | `datetime64[ns, UTC]` | **NO** | **YES** | Primary Index. Monotonically increasing, strictly UTC. |
| `open` | `float64` | **NO** | **YES** | Bar opening price. Strictly $> 0.0$. |
| `high` | `float64` | **NO** | **YES** | Bar highest price. Must satisfy $High \ge \max(Open, Close, Low)$. |
| `low` | `float64` | **NO** | **YES** | Bar lowest price. Must satisfy $Low \le \min(Open, Close, High)$. |
| `close` | `float64` | **NO** | **YES** | Bar closing price. Strictly $> 0.0$. |
| `tick_volume` | `int64` | **NO** | **YES** | Number of tick updates within the bar interval. Must be $\ge 0$. |
| `spread_pts` | `float64` | **NO** | **YES** | Average or bar-close bid-ask spread in points. Must be $\ge 0$. |
| `real_volume` | `int64` | **YES** | **OPTIONAL** | Executed trade volume in contracts (if provided by venue). |

---

## 3. Timezone & Trading Session Standards

1. **Strict UTC Timestamping (`Rule M3-02`)**:
   - All dataset timestamps must be timezone-aware and normalized to Coordinated Universal Time (UTC).
   - Local broker server time (e.g. EET/EST) must be converted deterministically to UTC during ingestion.
2. **Session Boundaries & Continuity (`Rule M3-01`)**:
   - The bullion market operates continuously from Sunday 22:00 UTC through Friday 21:00 UTC, with a daily 1-hour session transition break between 21:00 and 22:00 UTC.
   - Weekend intervals (Friday 21:00 UTC to Sunday 22:00 UTC) and scheduled holiday closures (e.g. Christmas, New Year's Day) are recognized as valid market downtime and are excluded from missing-bar penalty counts.
   - Intrasession missing-bar fraction must not exceed **0.05%** of the expected active trading universe.

---

## 4. Anti-Corruption & Quality Firewalls

In compliance with the **Stage 3 Data Quality Charter** and **ADR-001**:
1. **Zero Silent Repair (`Rule M3-05`)**:
   - Linear interpolation or synthetic curve-fitting across missing price bars is **strictly prohibited** as it injects look-ahead leakage.
   - Missing bars must either be explicitly identified or forward-filled via Zero-Order-Hold (ZOH) with volume set strictly to $0$.
2. **Price Sanity Firewall (`Rule M3-04`)**:
   - Any bar violating $High < \max(Open, Close)$ or $Low > \min(Open, Close)$ triggers immediate dataset rejection.
3. **Cryptographic Lineage (`Rule M3-07`)**:
   - Raw data files are cold-archived under `data/raw/` in an immutable state.
   - Clean datasets under `data/processed/` must carry a SHA-256 fingerprint recorded in the master manifest.
4. **Protected Out-of-Sample Vault**:
   - Tier 4 ($20\%$) data is partitioned chronologically and isolated into `data/vault/` with governance locking enabled.
