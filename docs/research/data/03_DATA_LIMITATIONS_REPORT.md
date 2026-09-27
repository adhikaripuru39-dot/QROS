# QROS Additional Data Limitations & Boundary Report: XAUUSD
**Report Identifier:** QROS-REP-DATA-003  
**Mission:** QROS-DATA-EXPANSION-001  
**Primary Asset:** XAUUSD  
**Status:** Approved Canonical Documentation  

---

## 1. Executive Summary

This document establishes the empirical boundaries, limitations, and operational constraints of the acquired MetaTrader 5 historical datasets for XAUUSD. In compliance with the **Bill of Rights: Traceability & Honesty** and the **Stage 3 Data Quality Charter**, QROS explicitly records known broker/feed limitations rather than presuming idealized market representations.

---

## 2. Identified Data Limitations & Mitigations

### A. Broker-Specific Terminal Buffer Ceilings
- **Limitation:** The connected MetaQuotes demo terminal enforces a standard buffer limit (`TerminalInfo.maxbars = 10,000`) per single API request.
- **Observed Impact:** Individual `copy_rates_from` calls requesting $> 10,000$ bars are rejected by the terminal with `Invalid params (-2)`.
- **Mitigation & Governance Rule:** `MT5IngestionAdapter` calibrates ingestion requests to $\le 9,999$ bars per slice. Long-horizon continuous series must utilize sequential chunking or multi-file consolidation with cryptographic deduplication.

### B. High-Frequency Time Horizon Truncation on Micro Timeframes
- **Limitation:** On M1 (1-minute) and M5 (5-minute) timeframes, broker server retention yields $9,999$ bars, translating to $9.5$ trading days for M1 and $52.0$ trading days for M5.
- **Observed Impact:** M1 data cannot support multi-year backtests or low-frequency macro cycle analysis.
- **Mitigation & Governance Rule:** M1 datasets are restricted to **Class I (High-Frequency Microstructure)** validation where trade velocity is high ($N \ge 1,000$ events over short durations). M5 datasets are restricted to **Class II (Intraday Momentum)**. Long-horizon holding models must use H1 (1.71 years) or D1 (7.75 years).

### C. Tick Volume vs. Real Consolidated Exchange Volume
- **Limitation:** Spot Gold (`XAUUSD`) is an over-the-counter (OTC) decentralized interbank market. MetaTrader 5 provides `tick_volume` (the frequency of price revisions received by the broker bridge) rather than consolidated centralized order book volume (`real_volume`).
- **Observed Impact:** `real_volume` is populated as $0$ in the OTC demo feed.
- **Mitigation & Governance Rule:** Quantitative research models must calibrate volume-weighted indicators strictly to `tick_volume` and recognize that tick velocity serves as an empirical proxy for liquidity rather than absolute contract count.

### D. Spread Quoting Dynamics
- **Limitation:** Ingested `spread_pts` reflects the broker bridge spread snapshot at bar close. Intrabar bid-ask spread spikes during extreme illiquidity or economic news releases may exceed the recorded bar-close spread.
- **Mitigation & Governance Rule:** The `TransactionCostModel` (`src/qros/pipeline/costs.py`) mandates conservative stress multipliers ($1.5\times \to 4\times$ spread expansion, slippage penalties, and execution latency buffers) to guarantee robustness against intrabar spread variability.

---

## 3. Tick Data Exclusion Decision Record

In adherence to the directive mandate ("Do not download tick data unless MT5 availability, storage requirements, and research value justify it. Document the decision."):

| Consideration Dimension | Evaluation & Findings |
| :--- | :--- |
| **Storage & I/O Overhead** | Multi-week tick archives generate $> 50,000,000$ records ($> 3\text{ GB}$ uncompressed), severely degrading rapid CI/CD test execution and local pipeline iteration speed. |
| **Research Value for Classes I–V** | 1-minute and 5-minute OHLCV bars with native tick volumes and spread points provide complete information for candlestick patterns, momentum signals, swing trends, and volatility regimes. |
| **Deterministic Reproducibility** | Nanosecond tick feeds across OTC brokers suffer from non-deterministic queuing jitter. 1-minute aggregated bars provide deterministic SHA-256 fingerprinting. |
| **Final Policy Decision** | **OMIT raw tick recording.** Focus research datasets on M1, M5, H1, and D1 OHLCV representations. |
