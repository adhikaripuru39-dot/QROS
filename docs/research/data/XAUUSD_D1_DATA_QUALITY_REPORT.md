# QROS Comprehensive Data Quality Report: XAUUSD (D1)
**Dataset Identifier:** `QROS-DATA-XAUUSD-D1-v3.0.0`  
**Asset / Symbol:** `XAUUSD`  
**Timeframe / Resolution:** `D1`  
**Date Audited:** `2026-08-15T02:58:04.672533+00:00`  
**Dataset SHA-256:** `8a15183849f5d140024464d6ddedc27d0007c1a358d8d7dabec94db8d19c9831`  
**Overall Quality Status:** **[APPROVED]**  

---

## 1. Executive Summary & Observations
- **Total Bars Ingested:** 4,500
- **Time Span:** 2009-02-27T00:00:00+00:00 $\rightarrow$ 2026-08-14T00:00:00+00:00 (17.46 Years)
- **Dataset SHA-256 Fingerprint:** `8a15183849f5d140024464d6ddedc27d0007c1a358d8d7dabec94db8d19c9831`
- **Data Quality Gate Outcome:** **APPROVED**

---

## 2. Stage 3 Quality Map Compliance Matrix

| Rule ID | Quality Dimension | Threshold / Requirement | Observed Value | Status |
| :--- | :--- | :--- | :--- | :--- |
| **M3-02** | Timestamp Integrity | Strictly UTC, monotonically increasing | Monotonic=True, TZ=UTC | **[PASS]** |
| **M3-03** | Duplicate Detection | Zero duplicate timestamps allowed | 0 duplicates | **[PASS]** |
| **M3-04** | Price Sanity & Boundary Check | High >= max(O,C,L), Low <= min(O,C,H), Price > 0 | Violations = 0 | **[PASS]** |
| **M3-01** | Grid Continuity & Completeness | Missing-bar fraction < 0.05% of daily active universe | Unexpected Gaps = 0 (0.000%) | **[PASS]** |
| **M3-05** | Missing-Data & Anti-Interpolation | Zero unhandled NaNs; zero linear interpolation | Null Values = 0 | **[PASS]** |
| **M3-07** | Cryptographic Fingerprint & Lineage | Deterministic SHA-256 fingerprint generated | SHA-256: 8a15183849f5d140... | **[PASS]** |
| **M3-08** | Overall Quality Sign-Off | 100% pass on all mandatory checks M3-01 to M3-07 | APPROVED | **[PASS]** |

---

## 3. Dataset Summary Statistics

| Metric | Value |
| :--- | :--- |
| Total Bars | 4,500.0000 |
| Min Price | 864.5400 |
| Max Price | 5,598.0300 |
| Mean Close | 1,735.2555 |
| Mean Tick Volume | 113,670.0482 |
| Mean Spread Pts | 15.0242 |
| Calendar Span Years | 17.4593 |

---

## 4. Detected Anomalies & Quality Log
- :white_check_mark: Zero data anomalies, corrupted records, or price violations detected.

---

## 5. Governance & Sign-Off Statement
In accordance with Stage 3 Data Quality Charter (`Rule M3-08`), this dataset is marked as **APPROVED**.
No look-ahead linear price interpolation was performed. Raw data has been fingerprinted and persisted.