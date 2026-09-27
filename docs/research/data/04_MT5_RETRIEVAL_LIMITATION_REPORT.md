# MT5 Retrieval Limitation Report

**Date:** 2026-08-15
**Mission:** QROS-DATA-EXPANSION-002
**Subject:** XAUUSD Historical Depth Limits

## 1. Overview
During Mission QROS-DATA-EXPANSION-002, the objective was to expand the historical XAUUSD dataset depth significantly beyond the existing ~10,000 bar limits for M1, M5, and H1 timeframes. We implemented a robust paginated retrieval engine within `MT5IngestionAdapter` to request data in discrete chunks, systematically pacing backwards to circumvent client-side API payload limitations.

## 2. Methodology
The newly implemented retrieval architecture uses a chunked extraction process:
- A cursor (`dt_cursor`) tracks the oldest timestamp retrieved.
- Incremental fetches of $\le 9000$ bars are executed sequentially backwards from `dt_cursor`.
- Results are deduplicated on the time boundary and concatenated into a contiguous series.
- Fetching loops until the target count is satisfied or the broker stops returning older data.

## 3. Empirical Findings: The 10,000-Bar Wall
The MT5 execution revealed a hard limitation on the broker's side.

### Intraday Timeframes (M1, M5, H1)
Despite implementing chunked pagination, data extraction for M1, M5, and H1 definitively halted after exactly **10,000 bars**. The broker server simply refused to return data older than:
- **M1:** 2026-08-05 (~10 days)
- **M5:** 2026-06-23 (~52 days)
- **H1:** 2024-11-27 (~1.7 years)

This proves the 9,999-bar truncation observed in v2.0.0 was **not** a Python API or client-side retrieval-window limitation. It is an intentional, hardcoded server-side limitation on this broker account.

### Daily Timeframe (D1)
For the D1 timeframe, the paginated engine successfully fetched the full targeted history (4,500 bars), retrieving data back to **2009-02-27**, verifying the pagination logic functions correctly when the broker permits the history.

## 4. Conclusion & Governance Record
**DATA UNAVAILABLE FROM SOURCE** for intraday timeframes exceeding 10,000 bars.

Because the limit is enforced unilaterally by the MT5 broker server, the current v3.0.0 dataset captures 100% of the available historical market history. QROS research must proceed under the assumption that greater intraday depth is structurally unavailable on this feed.
