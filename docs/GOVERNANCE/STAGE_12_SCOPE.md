## Stage 12 – Replication Scope Document

**Purpose** – This document defines the *exact* boundaries of the Replication stage (Stage 12) for QROS. It clarifies which activities are permitted, which are prohibited, and the required inputs and outputs. It is referenced by the Charter, Checklist, and Replication‑Rule Map to guarantee a single, enforceable interpretation.

---

### 1. In‑Scope Activities
| Activity | Description | Authority Reference |
|----------|-------------|----------------------|
| **Definition of Replication Windows** | Specify the start‑to‑end timestamps for the original validation run that must be re‑executed. | Section 3 of the Charter |
| **Operator Separation** | Ensure the replication is performed by a qualified individual who was not involved in the original validation. | Checklist item 5 |
| **Environment Separation** | Execute the replication on a machine/container that differs in at least one of: OS version, hardware architecture, runtime library versions. | Checklist item 4 |
| **Data Snapshot Reuse** | Use the *exact* immutable data snapshots (train/validation) that were used in the original validation run. | Checklist item 2 |
| **Code/Version Parity** | Run the identical code base (commit hash, package versions) as used for the original validation. | Checklist item 3 |
| **Tolerance Definition** | Define acceptable deviation bounds for each performance metric (absolute/relative). | Replication‑Rule Map § 5 |
| **Artifact Generation** | Produce immutable logs, environment manifests, metric reports, and signed sign‑off forms. | Replication‑Rule Map § 6 |
| **Peer‑Review Coordination** | Coordinate at‑least two senior researcher sign‑offs on the replication outcome. | Checklist item 10 |
| **Audit Trail Updates** | Append SHA‑256 checksums, timestamps, and signer IDs to the central audit ledger. | Checklist item 7 |

---

### 2. Out‑of‑Scope Activities
| Activity | Reason for Exclusion |
|----------|----------------------|
| **Implementation of Replication Engine** | Stage 12 is governance‑only; actual execution code resides in Stage 13 or downstream stages. |
| **Live Trading, Order Dispatch, or Execution** | Prohibited by Rules 40‑42 – belong to the Execution stage. |
| **Strategy Development** | Strategy work occurs in earlier stages; Stage 12 validates only reproducibility. |
| **Generation of New Data** | Data creation is governed by Stage 2 Data Foundation; Stage 12 must consume immutable snapshots only. |
| **Statistical Research Beyond Tolerances** | Any additional hypothesis testing is to be performed in Stage 8 or Stage 9, not here. |

---

### 3. Input Requirements (must be provided before replication can start)
1. **Immutable Data Snapshots** – the exact `train_<timestamp>.parquet` and `val_<timestamp>.parquet` files used in the original validation, with SHA‑256 checksum recorded.
2. **Code Artifact** – a commit hash, Docker image digest, or packaged version identifier for the exact code used in the original validation.
3. **Replication Configuration** – `replication_config.yaml` containing:
   - Operator identifier.
   - Environment manifest (OS, CPU, libraries).
   - Tolerance table for metric deviations.
   - Random seed (if any) used in the original run.
4. **Risk & Constraint Parameters** – any hard limits (e.g., max drawdown) that must be enforced during replication.

---

### 4. Output Requirements (must be produced and archived)
1. **Signed Replication‑Rule Map** – this document signed by Replication Owner and Compliance Officer, stored as `replication_rule_map_<timestamp>.pdf`.
2. **Environment Manifest** – `environment_<timestamp>.json` detailing OS, hardware, library versions, stored with checksum.
3. **Replication Log** – `replication_log_<timestamp>.json` containing timestamps, seed, library versions, and checksum of each input artifact.
4. **Metrics Report** – CSV and PDF (`metrics_report_<timestamp>.csv/pdf`) summarising original vs. replicated metrics and deviation percentages.
5. **Operator Acknowledgement Form** – signed PDF confirming independent execution.
6. **Peer‑Review Sign‑Off Forms** – scanned PDFs of two senior researcher approvals.
7. **Compliance Checklist** – completed `STAGE_12_CHECKLIST.md` with all items marked ✓.
8. **Audit Ledger Entry** – a line appended to `audit.log` with timestamps, checksums, and signer IDs.

All artefacts must be stored in `artifacts/replication/` on write‑once, read‑many (WORM) storage.

---

### 5. Enforcement Mechanisms
- **Automated Gating** – The QROS pipeline will refuse to advance to Stage 13 unless every output file listed above exists, has a matching checksum, and the Replication‑Rule Map is signed by both the Replication Owner and the Compliance Officer.
- **Immutable Storage** – All artefacts are written to WORM storage; any deletion or alteration triggers an audit violation.
- **Change‑Control** – Any modification to `replication_config.yaml` after a run requires a new replication request and re‑approval.
- **Audit Alerts** – Missing or mismatched checksums generate an immediate alert to the Compliance Officer and block downstream pipelines.

---

**Version History**
- v1.0 – Created 2026‑08‑12 (Author: QROS Governance Team)

---

*All parties must adhere strictly to this scope. Any deviation must be documented, justified, and approved by the Governance Board before proceeding.*