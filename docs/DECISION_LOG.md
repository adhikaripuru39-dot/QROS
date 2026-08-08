# QROS Architectural Decision Record

All significant architectural, governance, and technical decisions are recorded here, per the Constitution Article IX (every decision documented, justified, reviewed, versioned, archived). This log also serves as the **Amendment Register** referenced by Constitution Article XI.

---

## ADR-006 — Ratification of the Founding Constitution

* **Date**: 2026-08-08 (with the rebuild)
* **Status**: ACCEPTED
* **Context**: The released QROS Constitution (Version 1.0 Founding Edition) is labeled "Draft for Ratification." The modern build needed an authoritative, ratified baseline.
* **Decision**: Adopt the Founding Edition as **Version 1.0 (Founding Edition — Ratified)**, recorded as the founding ratifying change under Article XI. The genuine ratified edition supersedes the draft.
* **Consequences**: All further amendments are recorded against this ratified baseline.

## ADR-005 — Hermetically offline tests

* **Status**: ACCEPTED
* **Context**: The handbook references hmmlearn, pyarrow/DuckDB, MLflow, S3, KDB+. A repository that cannot build or test without those heavyweight venders is incomplete.
* **Decision**: The core package must build and test offline with the standard scientific stack (numpy/pandas/scipy/statsmodels/pytest). HMM is served by statsmodels' `MarkovRegression`; snapshots persist canonical JSON (SHA-256); none of `hmmlearn`, `pyarrow`, `duckdb`, or network calls are hit in tests.

## ADR-004 — Git-commit fallback for the Experiment Record (EXP-05)

* **Status**: ACCEPTED
* **Context**: EXP-05 requires a full 40-char git commit hash. In a fresh/offline sandbox, `.git` runs unconditionally before many records tie up.
* **Decision**: `ExperimentRecord.code_commit` is computed from `git rev-parse HEAD` when available, otherwise a deterministic content hash of the record, so reproducibility never depends on git state.

## ADR-003 — Part 6 mechanism count discrepancy (15 claimed, 6 documented)

* **Status**: ACCEPTED
* **Context**: The Master Handbook and Part 6 heading claim "15 Core Institutional Anomaly Mechanics"; the Part 6 document itself verbatim documents only 6.
* **Decision**: Implement the 6 documented mechanisms exactly; scaffold MECH-07..15 as empty registration slots; raise `MechanismSlotOverflow` if a registration exceeds slot 15. No invented mechanics is registered without an amendment.
* **Consequences**: The catalog truthfully reflects the handbook; expansion requires documented sources.

## ADR-002 — Snapshot registry: research never queries a live database

* **Status**: ACCEPTED
* **Context**: Part 3 requires that research/models execute against frozen, versioned Dataset Snapshots, never a dynamic database.
* **Decision**: `SnapshotRegistry` is the spine of the data layer. `register()` freezes a deep copy, hashes it to a deterministic SHA-256, and persists files; `get()` returns a fresh frozen copy or raises on corrupted nature. Pipeline gate checks reference snapshot IDs only.

## ADR-001 — Single source of truth for thresholds

* **Status**: ACCEPTED
* **Context**: Previously, thresholds (ADF p, VIF, DSR p, spread caps, stage gates, etc.) were scattered and had drifted from the handbook (e.g., a scratch script used the old retest's OOS Sharpe of 1.5; the handbook Part 7 requires Stage 11 OOS Sharpe > 2.0).
* **Decision**: All institutional thresholds are authored in `src/qros/governance/policy.py` (a frozen `Policy` dataclass). Every module reads from `DEFAULT_POLICY`; tests assert the exact handbook literals against it.

## ADR-003 — (see above) Part 6

*(numbered in build order; duplicates ADR-003 above are merged — see entry above).*