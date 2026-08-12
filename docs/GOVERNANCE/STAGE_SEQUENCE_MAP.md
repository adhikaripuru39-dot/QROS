# QROS — Stage Order Map
Translates the Master Handbook (Parts 1–10, 15-stage pipeline) into the **allowed** sequence of work. Stage 1 Governance Lock gates everything; no later stage may begin until it passes.

## 0. The gate: Stage 1 Governance Lock (THIS PACKAGE)
- **Allowed:** documentation, scope/inputs/outputs/edge-confirmation definition, threshold authorship as *policy text*.
- **Prohibited:** any engine, research, backtest, or execution code.
- **Exit:** all four artifacts present, traceable, and approved; no implementation produced.
- **Do not proceed** past this gate until **scope, inputs, outputs, and edge confirmation are documented AND approved** (see `STAGE_1_CHECKLIST.md`, gate G0).

## A. Governance lock sequence (Part-independent; precedes all research)

| # | Action | Governing source | Allowed in Stage 1? |
| :- | :--- | :--- | :-: |
| L0 | Read + reconcile Constitution, Founding Governance, Handbook Parts 1–10 | Constitution Art. IX | ✅ |
| L1 | Define scope, inputs, outputs, edge confirmation | Charter §7 | ✅ |
| L2 | Author thresholds/gates as *policy text* (not code) | Part 8; HANDBOOK_INDEX (policy.py) | ✅ |
| L3 | Resolve ratification discrepancy (draft vs ADR-006) in decision log | Constitution Art. XI | ✅ |

## B. Research pipeline — allowed sequence (Handbook Part 7)

| Stage | Name | Handbook Part | Key governing threshold | Forbidden before lock? |
| :-: | :--- | :--- | :--- | :-: |
| 1 | Idea Generation | Part 6 | Peer review by QR team | ⛔ Yes |
| 2 | Literature Review | Part 6 | Novelty vs published work | ⛔ Yes |
| 3 | Theory Formation | Part 6 | Head of Research approval | ⛔ Yes |
| 4 | Hypothesis Creation | Part 5 | 22-field HYP, SHA-256 lock | ⛔ Yes |
| 5 | Data Collection | Part 1 | DE lineage audit | ⛔ Yes |
| 6 | Data Cleaning | Part 2 | zero bad-tick + timestamp audit | ⛔ Yes |
| 7 | Feature Engineering | Part 4 | ADF p < 0.05, no look-ahead scaling | ⛔ Yes |
| 8 | Exploratory Analysis | Part 4 | VIF < 10.0 | ⛔ Yes |
| 9 | Statistical Testing | Part 8 | t-stat > 3.0, p < 0.001 | ⛔ Yes |
| 10 | Robustness Testing | Part 7 | stable across ±50% parameter shift | ⛔ Yes |
| 11 | Walk-Forward Validation | Part 8 | OOS Sharpe > 2.0, MaxDD < 15% | ⛔ Yes |
| 12 | Replication | Part 5 | independent QR, >99.9% correlation | ⛔ Yes |
| 13 | Documentation | Art. IX | peer-review sign-off | ⛔ Yes |
| 14 | Research Approval | Art. VI | IC sign-off (Head + Risk) | ⛔ Yes |
| 15 | Model Development | Part 7 | hand-off to Quant Dev | ⛔ Yes |

Every stage requires zero gate violations and formal sign-off before advancing; **retroactive threshold relaxation is prohibited** (Part 7, Quality Gate Failure Rule).

## C. Domain → handbook part map (from HANDBOOK_INDEX)

| Domain | Part | Primary module (target) | Stage 1 action |
| :--- | :-: | :--- | :--- |
| Data Collection | 1 | `schemas/`, `governance/roles.py` | specify only |
| Data Quality | 2 | `data/quality.py` | specify only |
| Data Engineering | 3 | `data/` (snapshot registry) | specify only |
| Feature Engineering | 4 | `features/` | specify only |
| Hypothesis Mgmt | 5 | `hypothesis/registry.py` | specify only |
| Hypothesis Gen | 6 | `hypothesis/mechanics.py` | specify only |
| Research Pipeline | 7 | `pipeline/stages.py` | specify only |
| Statistical Method | 8 | `stats/` | specify only |
| Experiment Tracking | 9 | `tracking/experiment.py` | specify only |
| Edge Discovery | 10 | `edges/` | specify only |

## D. Hard stops (do-not-proceed triggers)
1. Scope, inputs, outputs, or edge confirmation **not** documented and approved → no Stage 2, no engine.
2. Any live/backtest execution before its stage gate passes → halt immediately (Part 7 failure rule).
3. Any ratification / production / approval claim not supported by the governing documents → strip and log.
4. Any threshold relaxed to make a result pass → halt and return to Stage 3 (Part 7).
