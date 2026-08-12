## Stage 11 – Walk‑Forward Validation Scope Document

**Purpose** – This document defines the *exact* boundaries of the Walk‑Forward Validation stage (Stage 11) for QROS. It delineates which activities are in‑scope, which are out‑of‑scope, and the permissible inputs and outputs. It is referenced by the Charter, the Compliance Checklist, and the Validation‑Rule Map to guarantee a single, enforceable interpretation.

---

### 1. In‑Scope Activities
| Activity | Description | Authority Reference |
|----------|-------------|----------------------|
| **Definition of Validation Windows** | Specify the length (in periods) of the training window, the validation window, and any test window used for final reporting. | Section 4 of the Charter |
| **Rolling‑Window Mechanics** | Document the step‑size (how far the windows advance each iteration) and any adjustments for calendar effects (e.g., month‑end). | Validation‑Rule Map § 1 |
| **Embargo & Purge Rules** | Apply a configurable embargo period after each training window and purge any data that could cause look‑ahead bias. | Validation‑Rule Map § 2 |
| **Regime Classification** | Define regimes (e.g., volatility, market‑state) and map each validation window to a regime label. | Validation‑Rule Map § 4 |
| **Acceptance Threshold Specification** | List quantitative thresholds (e.g., Sharpe > 1.2, p‑value < 0.05) and qualitative criteria (e.g., no breach of risk limits). | Validation‑Rule Map § 3 |
| **Artifact Generation** | Produce immutable snapshots, logs, metric reports, and a signed validation‑rule map for each model candidate. | Validation‑Rule Map § 5‑6 |
| **Peer Review Coordination** | Coordinate at‑least two senior researcher sign‑offs on the validation outcome. | Checklist item 11 |
| **Audit Trail Updates** | Append SHA‑256 checksums, timestamps, and environment metadata to the central audit ledger. | Checklist items 2‑4, 8 |

---

### 2. Out‑of‑Scope Activities
| Activity | Reason for Exclusion |
|----------|----------------------|
| **Implementation of the validation engine** | Stage 11 is governance‑only; actual code resides in Stage 12 or downstream stages. |
| **Live trading, order dispatch, or execution** | Prohibited by Rules 40‑42 – these belong to the Execution stage. |
| **Strategy development or back‑testing outside the prescribed walk‑forward framework** | Violates Rule 41 – strategy work occurs in earlier stages; Stage 11 validates only pre‑approved results. |
| **Generation of new data** | Data creation is governed by Stage 2 Data Foundation; Stage 11 must consume immutable snapshots only. |
| **Statistical research beyond the defined acceptance thresholds** | Any additional hypothesis testing is to be performed in Stage 8 or Stage 9, not here. |

---

### 3. Input Requirements (must be provided before validation can start)
1. **Data Snapshots** – immutable CSV/Parquet files for the full historical period, version‑controlled with checksum.
2. **Model Artifact** – serialized model or pipeline definition referenced in the validation request.
3. **Configuration File** – `validation_config.yaml` containing window lengths, step size, embargo length, and regime definitions.
4. **Risk & Constraint Parameters** – any hard limits that must be enforced during validation (e.g., max drawdown).

---

### 4. Output Requirements (must be produced and archived)
1. **Signed Validation‑Rule Map** – immutable PDF/MD file stored in `artifacts/validation/`.
2. **Training & Validation Window Checksums** – recorded in `audit/logs/`.
3. **Metrics Report** – CSV and PDF of out‑of‑sample performance, statistical significance, and regime‑specific results.
4. **Peer‑Review Sign‑Off Forms** – scanned PDFs uploaded to the audit repository.
5. **Compliance Checklist** – completed `STAGE_11_CHECKLIST.md` with all items marked ✓.

---

### 5. Enforcement Mechanisms
- **Automated Gating** – The QROS pipeline will refuse to advance to Stage 12 unless every output file listed above exists, has a matching checksum, and the Validation‑Rule Map is signed by the Validation Owner and Compliance Officer.
- **Immutable Storage** – All artifacts are written to write‑once, read‑many (WORM) storage; deletion or alteration triggers an audit violation.
- **Change‑Control** – Any modification to the `validation_config.yaml` after a run requires a new validation request and re‑approval.
- **Audit Alerts** – Missing or mismatched checksums generate an immediate alert to the Compliance Officer and block downstream pipelines.

---

**Version History**
- v1.0 – Created 2026‑08‑12 (Author: QROS Governance Team)

---

*All parties must adhere strictly to this scope. Any deviation must be documented, justified, and approved by the Governance Board before proceeding.*