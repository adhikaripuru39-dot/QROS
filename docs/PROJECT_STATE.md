# QROS Project State

**Current Date**: 2026-08-08
**Governance Stage**: Handbook Baseline — complete 15-stage research framework
**Production Status**: `NOT APPROVED` (no strategy deployed)

---

## Executive Summary

This repository was rebuilt from the ground up **exclusively from the QROS Master
Research Handbook (Parts 1-10)** and the ratified QROS Constitution. The earlier
legacy repo (which had drifted to a non-handbook 9-stage gate scheme) was removed
and its contents preserved in a backup archive. The current build implements the
handbook's institutional framework as a working, offline-tested Python package.

## Deliverables

| Area | Handbook Source | Status |
| :--- | :--- | :--- |
| Governance docs (ratified Constitution + founding docs) | Constitution, Founding Governance | ✅ docs/GOVERNANCE/ |
| 13 financial market data types + 5 vendor classes | Part 1 | ✅ schemas |
| Data quality suite (anomalies + 8-bias audit) | Part 2 | ✅ data/quality |
| Storage tiers, partition convention, snapshot registry | Part 3 | ✅ data/ |
| Feature transforms (fracdiff, OBI, GK vol, VPIN) + ADF/VIF | Part 4 | ✅ features |
| 22-field HYP registry + SHA-256 lock | Part 5 | ✅ hypothesis |
| Anomaly mechanics catalog (6 documented of 15) + regime | Part 6 | ✅ hypothesis |
| 15-stage gatekeeper pipeline | Part 7 | ✅ pipeline |
| DSR / FDR-BH / FWER-Holm / CPCV / bootstrap | Part 8 | ✅ stats |
| 17-field experiment tracking | Part 9 | ✅ tracking |
| Edge classification + 5 false-edge diagnostics | Part 10 | ✅ edges |
| CLI (`qros`) | all | ✅ cli |

## Verification

```bash
py -m pytest -q          # offline, hermetic
py -m qros stage list    # 15 stages
py -m qros policy        # institutional thresholds
```

## ADR / Amendment Register

See `docs/DECISION_LOG.md` (ADR-001..006), which doubles as the Article XI register.