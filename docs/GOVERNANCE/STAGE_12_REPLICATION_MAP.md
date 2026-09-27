## Stage 12 – Independent Replication Rule Map

**Purpose** – This rule map enumerates the concrete replication conventions, independence criteria, artifact requirements, tolerances, and gating conditions that govern the Independent Replication stage (Stage 12) of QROS. It is referenced by the Charter, Checklist, Scope, and Governance Board to enforce compliance before any result may progress to Stage 13.

---

### 1. Independence Requirements
| Requirement | Description | Verification Method |
|-------------|-------------|----------------------|
| **Operator Separation** | The replication must be executed by a qualified individual who was not involved in the original validation run. | Signed Operator Acknowledgement Form (see Checklist item 5). |
| **Environment Separation** | The replication must run on a compute environment that differs in at least one of: OS version, hardware architecture, or runtime library versions. | Environment manifest `environment_<timestamp>.json` with checksum logged (Checklist item 4). |
| **Temporal Independence** | Replication must be performed at a later calendar date than the original validation, ensuring no shared in‑memory state. | Timestamp recorded in `replication_log_<timestamp>.json`. |
| **Process Isolation** | Execution must occur in a clean, isolated container or VM with no lingering processes from the original run. | Container/VM ID recorded; audit confirms isolation. |

---

### 2. Operator / Environment Separation Details
- **Operator ID** – Unique identifier (e.g., employee ID, badge number) of the replicator, recorded in the Operator Acknowledgement Form.
- **Environment Manifest Fields** –
  - `os_name` and `os_version`
  - `cpu_architecture`
  - `kernel_version`
  - `runtime_libs` (list of major library versions, e.g., Python, NumPy, pandas)
  - `container_image` (Docker/Singularity image digest)
- **Separation Validation** – A comparison script (run by the governance pipeline, not by the user) asserts that at least one manifest field differs from the original validation environment.

---

### 3. Dataset & Snapshot Reuse Rules
| Rule | Requirement | Verification |
|------|-------------|--------------|
| **Exact Snapshot Usage** | Replication must use the *identical* immutable data snapshots (train/validation) that were used for the original validation. | SHA‑256 checksum of each snapshot recorded in `replication_log.json` and matched against the original validation log. |
| **No Re‑generation** | Data preprocessing steps must not be re‑run; the snapshots are consumed directly. | Absence of any preprocessing scripts in the replication run log. |
| **Versioned Snapshot Storage** | Snapshots must reside in write‑once storage with version tags (e.g., `snapshot_v2026-08-01`). | Storage system enforces WORM; timestamp recorded. |

---

### 4. Code / Version Parity Requirements
1. **Commit Hash Equality** – The exact Git commit SHA used in the original validation must be specified and used for replication.
2. **Dependency Freeze** – All package versions (e.g., `requirements.txt`, `environment.yml`) must match the original list exactly.
3. **Runtime Environment** – The same interpreter/VM version (e.g., Python 3.11.2) must be used, unless the environment separation rule already forces a difference; any intentional version divergence must be documented and approved by the Replication Owner.
4. **Configuration Consistency** – All configuration files (`validation_config.yaml`, model hyper‑parameters) must be identical; any deviation triggers a mandatory re‑approval.

Verification is performed by comparing the recorded `code_artifact` identifier and `dependency_manifest` against the originals; mismatches cause an immediate block.

---

### 5. Result‑Matching Tolerances
| Metric | Original Value (Reference) | Allowed Deviation | Tolerance Type |
|--------|----------------------------|-------------------|---------------|
| **Sharpe Ratio** | `S_ref` | ± 0.05 absolute *or* ± 5 % relative (whichever is stricter) | Absolute / Relative |
| **Maximum Drawdown** | `DD_ref` | ≤ + 2 % absolute increase (i.e., replicated drawdown must not exceed `DD_ref` + 2 %) | Absolute |
| **Sortino Ratio** | `So_ref` | ± 0.04 absolute | Absolute |
| **Information Ratio** | `IR_ref` | ± 0.03 absolute | Absolute |
| **Metric‑Level p‑value** | `p_ref` (must be ≤ 0.05) | Replicated p‑value must also be ≤ 0.05 | Threshold |
| **Time‑Series Correlation** | `ρ_ref` (correlation of returns across windows) | ≥ 0.90 | Minimum |

*All tolerances are **hard gating** – if any metric falls outside its allowed deviation, the replication is deemed **failed** and the result cannot advance.

---

### 6. Discrepancy Handling & Root‑Cause Logging
1. **Discrepancy Detection** – The replication pipeline automatically computes the deviation for each metric and flags any that exceed tolerance.
2. **Root‑Cause Log** – When a discrepancy is flagged, the operator must fill out a `discrepancy_report_<timestamp>.md` containing:
   - Metric(s) that failed.
   - Observed vs. reference values.
   - Potential causes (environment drift, nondeterministic algorithm, data corruption, hidden state).
   - Investigation steps taken.
3. **Escalation Path** – If the root‑cause cannot be resolved within the replication run, the issue is escalated to the **Governance Board** for a formal review. The board may:
   - Approve a one‑time tolerance relaxation (recorded as an amendment).
   - Require a re‑run in a third, independent environment.
   - Reject the result outright.
4. **Logging Requirements** – All discrepancy reports, investigation notes, and board decisions are stored as immutable artifacts under `artifacts/replication/discrepancies/` with SHA‑256 checksums.

---

### 7. Do‑Not‑Proceed List (Blocking Conditions)
The following conditions **automatically block** any downstream Stage 13 activities, strategy implementation, uncontrolled back‑testing, execution, or approval claims:

1. **Missing or corrupted artifacts** – Any file listed in Section 6 is absent, checksum mismatched, or unreadable.
2. **Tolerance violation** – Any metric exceeds its allowed deviation (Section 5).
3. **Operator/Environment non‑separation** – Operator is the same as original validation, or environment manifest matches exactly (no separation).
4. **Data snapshot mismatch** – SHA‑256 of any data snapshot differs from the original validation snapshot.
5. **Code/version mismatch without approved exception** – Commit hash or dependency versions differ and no documented approval exists.
6. **Unsigned Replication‑Rule Map** – The map is not signed by both Replication Owner and Compliance Officer.
7. **Incomplete checklist** – Any item in `STAGE_12_CHECKLIST.md` remains unchecked after final review.
8. **Hidden or selective replication** – The replication run does not replay the full original pipeline (e.g., skipped steps, partial data). Detected via execution trace audit.
9. **Execution of trading logic** – Presence of order‑dispatch or live‑trading code in the replication run.
10. **Unapproved strategy changes** – Any alteration to strategy parameters or logic that was not part of the original validated result.

**If any of the above conditions are true, the result must be **rejected**, the Compliance Officer records the rejection, and the pipeline halts.**

---

### 8. Governance Review & Sign‑Off
| Role | Signature | Date |
|------|-----------|------|
| **Replication Owner** | _______________________ | ________ |
| **Compliance Officer** | _______________________ | ________ |
| **Research Lead (Submitter)** | _______________________ | ________ |
| **Operator (Replicator)** | _______________________ | ________ |
| **Peer Reviewer 1** | _______________________ | ________ |
| **Peer Reviewer 2** | _______________________ | ________ |

All signatures must be captured electronically; the signed PDF becomes the immutable `replication_rule_map_<timestamp>.pdf` referenced in the checklist.

---

**Version History**
- v1.0 – 2026‑08‑12 (initial governance package draft)

---

*This rule map is the authoritative source for Stage 12 Independent Replication. Any deviation must be documented, justified, and approved by the Governance Board before proceeding.*