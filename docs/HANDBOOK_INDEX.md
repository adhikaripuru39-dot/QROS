# QROS Handbook — Implementation Traceability Index

Map from the QROS Master Research Handbook (Parts 1-10) and Constitution to their
implementation modules. This is the constitutionally-required traceability record
(Article IX: decisions and requirements are documented, versioned, archived).

## Governing documents

| Document | Module / File |
| :--- | :--- |
| Constitution (11 articles) | `docs/GOVERNANCE/constitution.md` · `governance/constitution.py` (register) |
| Bill of Rights / Responsibilities / Code of Scientific Conduct | `docs/GOVERNANCE/*.md` |
| Engineering Manifesto (5th founding doc) | `docs/GOVERNANCE/engineering_manifesto.md` |
| Decision log / Amendment register | `docs/DECISION_LOG.md` |

## Handbook Parts → implementation

| Part | Domain | Primary Module | Deliverables |
| :--- | :--- | :--- | :--- |
| 1 | Data Collection Framework | `schemas/data_types.py`, `schemas/vendors.py` | 13 data types, 5 vendor classes, L1/L2/L3 |
| 2 | Data Quality Management | `data/quality.py` | anomaly detection, 8-bias audit |
| 3 | Data Engineering | `data/engineering.py`, `data/snapshot.py`, `data/feature_store.py` | tiers, partitioning, frozen snapshots, feature store |
| 4 | Feature Engineering | `features/transforms.py`, `features/validate.py`, `features/catalogue.py` | fracdiff, OBI, GK, VPIN, ADF/VIF |
| 5 | Hypothesis Management | `hypothesis/registry.py` · `schemas/fields.py` | 22-field HYP + SHA-256 lock |
| 6 | Hypothesis Generation | `hypothesis/mechanics.py`, `hypothesis/regime.py` | anomaly mechanisms, regime detection |
| 7 | Research Pipeline | `pipeline/stages.py`, `gates.py`, `state_machine.py` | 15-stage gatekeeper workflow |
| 8 | Statistical Methodology | `stats/sharpe.py`, `multiple_testing.py`, `cpcv.py`, `bootstrap.py` | DSR, FDR-BH, FWER-Holm, CPCV |
| 9 | Experiment Tracking | `tracking/experiment.py` | 17-field EXP record, trial count → DSR |
| 10 | Edge Discovery | `edges/taxonomy.py`, `edges/audit.py`, `stats/timeseries.py` | edge classification, 5 false-edge diagnostics |

## Institutional roles (Part 1 ch.1.3)

| Role | Code |
| :--- | :--- |
| Data Engineer, Quant Researcher, Statistical Researcher, Data Governance Officer | `governance/roles.py` |
| Head of Research, Lead Statistician, Investment Committee, Quant Dev | `governance/roles.py` |

## Threshold governance

Every numeric threshold (ADF p, VIF, DSR p, FDR q, stage gates, edge metrics) is
authored in `governance/policy.py` (single source of truth, ADR-001).