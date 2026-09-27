## Stage 12 – Independent Replication Compliance Checklist

All items **must** be completed, verified, and signed off before any research result may advance to Stage 13.  Any unchecked item blocks progress.

| # | Item | Responsible Role | Verification Method | Status |
|---|------|------------------|----------------------|--------|
| 1 | Replication‑Rule Map approved (see **STAGE_12_REPLICATION_MAP.md**) | Replication Owner | Review of signed map | ☐ |
| 2 | Immutable data snapshot for replication captured and archived | Data Steward | SHA‑256 checksum recorded in log | ☐ |
| 3 | Exact code version (commit hash / package version) documented and archived | Data Steward | Version identifier recorded in audit log | ☐ |
| 4 | Distinct compute environment defined (OS, hardware, libraries) and logged | Data Steward | Environment manifest stored with checksum | ☐ |
| 5 | Operator separation confirmed – replication performed by a different qualified individual | Operator (Replicator) | Signed operator acknowledgment form | ☐ |
| 6 | Acceptance tolerance values (metric deviation limits) defined and signed | Replication Owner | Tolerance table signed by Compliance Officer | ☐ |
| 7 | Replication run logs (random seed, library versions, timestamps) stored in immutable storage | Data Steward | Log hash stored in audit trail | ☐ |
| 8 | Metrics report (replicated performance, deviations, statistical significance) generated | Operator (Replicator) | PDF/CSV artifact attached to audit log | ☐ |
| 9 | All artifacts listed in **STAGE_12_REPLICATION_MAP.md** are present and accessible | Replication Owner | Artifact checklist cross‑checked | ☐ |
|10 | Peer‑review sign‑off by at least two senior researchers | Peer Reviewers | Signed review forms uploaded | ☐ |
|11 | Final compliance sign‑off by Compliance Officer | Compliance Officer | Signed compliance checklist uploaded | ☐ |
|12 | No hidden or selective replication detected (full pipeline replay) | Compliance Officer | Review of execution trace confirms complete run | ☐ |

**Blocking rule:** if any item remains unchecked (☐) after the final review, the result **must not** proceed to Stage 13.
