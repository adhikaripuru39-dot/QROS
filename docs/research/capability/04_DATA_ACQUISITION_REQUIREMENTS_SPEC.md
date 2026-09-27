# QROS Data Acquisition Requirements Specification

**Document ID:** `QROS-SPEC-DATA-002`  
**Mission:** QROS-RESEARCH-010  
**Status:** Mandatory Engineering Specification  
**Authority:** QROS Architecture Authority  
**Date:** 2026-08-15  

---

## 1. Specification Objectives

This specification defines the exact technical requirements, schemas, normalization standards, and governance protocols for acquiring external data into the QROS research vault across three priority data categories:
1. **Category A:** Deep Multi-Year Historical Intraday/Tick Data (XAUUSD & Precious Metals).
2. **Category B:** Macroeconomic & Intermarket Time Series (FRED & Financial Fundamentals).
3. **Category C:** Institutional Positioning & Commitment of Traders (CFTC COT).

---

## 2. Category A: Historical Tick & Intraday Specifications

### 2.1 Asset Scope
- Primary: `XAUUSD` (Spot Gold / USD)
- Secondary: `XAGUSD` (Spot Silver / USD), `EURUSD` (Euro / USD), `DXY` (US Dollar Index proxy)

### 2.2 Timeframe & Resolution Requirements
- **M1 (1-Minute Aggregated):** Minimum 10 continuous calendar years (2014–2024+).
- **Tick-Level Bid/Ask Quotes:** Minimum 5 continuous calendar years for microstructure and intraday session research.

### 2.3 Required Data Schema (Parquet Format)
```python
# M1 Historical Schema
{
    "timestamp": "datetime64[ns, UTC]",  # Mandatory UTC timezone
    "open_bid": "float64",
    "high_bid": "float64",
    "low_bid": "float64",
    "close_bid": "float64",
    "open_ask": "float64",
    "high_ask": "float64",
    "low_ask": "float64",
    "close_ask": "float64",
    "spread_pts": "float64",  # (close_ask - close_bid) in price points
    "volume": "float64",
}
```

---

## 3. Category B: Macroeconomic & Real Yield Specifications

### 3.1 Source & Provider
- **Provider:** Federal Reserve Bank of St. Louis (FRED API)
- **Historical Span:** Minimum 20 continuous calendar years (2004–2024+).
- **Frequency:** Daily (`1D`), released at close of business.

### 3.2 Required FRED Series Identifiers
| Series ID | Description | Economic Role in Gold Pricing |
| :--- | :--- | :--- |
| `DFII10` | 10-Year Treasury Inflation-Indexed Security, Constant Maturity (Real Yield) | Primary driver of gold's institutional opportunity cost. |
| `DGS10` | 10-Year Treasury Constant Maturity Rate (Nominal Yield) | Benchmark risk-free discount rate. |
| `T10YIE` | 10-Year Breakeven Inflation Rate | Market-implied long-term inflation expectations. |
| `DTWEXBGS` | Trade Weighted U.S. Dollar Index (Broad Goods and Services) | Comprehensive fiat purchasing power proxy. |
| `FEDFUNDS` | Effective Federal Funds Rate | Short-term policy rate benchmark. |
| `GVZCLS` | Cboe Gold Volatility Index | Implied volatility expectations on gold options. |

### 3.3 Macro Data Normalization Protocol
- **Point-in-Time Publication Lag:** Macro data released at 16:00 EST must be lagged to timestamp `23:59:59 UTC` to prevent intraday look-ahead bias.
- **Holiday Forward-Filling:** Non-trading bank holidays in the US bond market must use forward-filled prior-day values with an explicit `is_interpolated=False` tracking flag.

---

## 4. Category C: Institutional CFTC Commitments of Traders (COT)

### 4.1 Source & Provider
- **Provider:** U.S. Commodity Futures Trading Commission (CFTC) Socrata Open Data API / Historical Archives.
- **Contract:** COMEX Gold (Commodity Code: `088691`), COMEX Silver (Commodity Code: `084691`).
- **Frequency:** Weekly (Released Fridays at 15:30 EST, reflecting Tuesday positions).

### 4.2 Required Fields & Lag Governance
```python
{
    "as_of_date": "date",  # Tuesday positioning date
    "report_date": "date",  # Friday release date
    "effective_trade_date": "datetime64[ns, UTC]",  # Sunday 22:00 UTC market open post-release
    "commercial_long": "int64",
    "commercial_short": "int64",
    "commercial_net": "int64",  # commercial_long - commercial_short
    "non_commercial_long": "int64",  # Managed Money / Speculators
    "non_commercial_short": "int64",
    "non_commercial_net": "int64",
    "total_open_interest": "int64",
}
```

> [!IMPORTANT]
> **Strict Point-in-Time COT Indexing:** Because COT data reflects Tuesday positioning but is released Friday evening, trades executing on Tuesday–Friday MUST NOT access that week's report. Data becomes eligible for trade conditioning ONLY on the following Monday open.

---

## 5. Ingestion Architecture & Quality Controls

All newly acquired datasets must pass the existing QROS data gateway (`src/qros/data/validation.py` & `quality.py`):
1. **Deterministic SHA-256 Hashing:** Raw and processed files hashed and registered in `DATASET_MANIFEST.json`.
2. **Chronological Monotonicity:** Zero duplicate timestamps, zero backwards jumps.
3. **Partitioning & Tier-4 Vaulting:** Automatic 4-tier chronological split (Tier 1: EDA 20%, Tier 2: Train 40%, Tier 3: Val 20%, Tier 4: Protected OOS 20% locked).
