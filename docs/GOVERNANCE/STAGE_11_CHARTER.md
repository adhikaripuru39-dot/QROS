## Stage 11 – Walk‑Forward Validation Charter

### 1. Purpose
Define the governed process by which QROS validates out‑of‑sample performance of research results using walk‑forward (rolling‑window) methodology. Ensure reproducibility, prevent data leakage, and enforce a barrier before any result may advance to subsequent stages.

### 2. Authority
- QROS Constitution (Draft for Ratification)
- Founding Governance Documents
- Master Handbook Parts 1‑11
- Prior Stage artifacts (Stages 1‑10)

### 3. Definitions
- **Walk‑Forward Validation** – iterative evaluation where a model is trained on a chronological “training window”, then validated on the immediately following “validation window”, moving forward in time.
- **Rolling‑Window** – windows shift forward by a fixed step (e.g., one period) while maintaining constant window lengths unless otherwise specified.
- **Embargo Period** – a buffer of data after the training window that is excluded from both training and validation to avoid look‑ahead bias.
- **Regime‑Aware Validation** – separate validation criteria for distinct market or data regimes (e.g., high volatility vs low volatility).

### 4. Governance Principles
- **Reproducibility** – All parameters, data snapshots, and code versions must be archived.
- **Leakage Prevention** – No forward‑looking information may enter the training set.
- **Threshold Enforcement** – Results must meet predefined acceptance criteria before progressing.
- **Auditability** – Full logs, data snapshots, and decision records must be retained.

### 5. Roles & Responsibilities
- **Validation Owner** – approves the validation rule map, oversees execution.
- **Data Steward** – provides immutable, time‑stamped data snapshots and enforces embargo.
- **Compliance Officer** – confirms checklist completion and signs off artifacts.
- **Research Lead** – submits candidate results for validation.

### 6. Deliverables
- Charter (this document)
- Compliance Checklist (STAGE_11_CHECKLIST.md)
- Scope Document (STAGE_11_SCOPE.md)
- Validation‑Rule Map (STAGE_11_VALIDATION_MAP.md)
- All artifacts listed in the Validation‑Rule Map

### 7. Review Cycle
1. Initial review by Validation Owner.
2. Peer review by at least two senior researchers.
3. Final sign‑off by Compliance Officer.

All items must be completed and signed before any result may move to Stage 12.
