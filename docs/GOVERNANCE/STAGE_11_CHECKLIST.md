## Stage 11 – Walk‑Forward Validation Compliance Checklist

The following items **must** be completed, verified, and signed off before any research result may advance to Stage 12.  All items are **mandatory**; any missing item blocks progress.

| # | Item | Responsible Role | Verification Method | Status |
|---|------|------------------|----------------------|--------|
| 1 | Validation‑Rule Map approved (see **STAGE_11_VALIDATION_MAP.md**) | Validation Owner | Review of signed map | ☐ |
| 2 | Immutable data snapshot for the **training window** captured and archived | Data Steward | SHA‑256 checksum recorded in log | ☐ |
| 3 | Immutable data snapshot for the **validation window** captured and archived | Data Steward | SHA‑256 checksum recorded in log | ☐ |
| 4 | Embargo period applied and documented | Data Steward | Timestamped embargo definition in config | ☐ |
| 5 | Rolling‑window parameters (window length, step size) defined and version‑controlled | Validation Owner | Config file versioned in repository | ☐ |
| 6 | Regime‑awareness criteria (e.g., volatility regime) defined and logged | Research Lead | Regime classification report generated | ☐ |
| 7 | Acceptance thresholds (metrics & statistical tests) defined and signed | Validation Owner | Threshold table signed by Compliance Officer | ☐ |
| 8 | Validation run logs (including random seed, library versions, timestamps) stored in immutable storage | Data Steward | Log hash stored in audit trail | ☐ |
| 9 | Metrics report (out‑of‑sample performance, risk stats, statistical significance) generated | Research Lead | PDF/CSV artefact attached to audit log | ☐ |
|10 | All artefacts listed in **STAGE_11_VALIDATION_MAP.md** are present and accessible | Validation Owner | Artifact checklist cross‑checked | ☐ |
|11 | Peer‑review sign‑off by at least two senior researchers | Peer Reviewers | Signed review forms uploaded | ☐ |
|12 | Final compliance sign‑off by Compliance Officer | Compliance Officer | Signed compliance checklist uploaded | ☐ |

**Blocking rule:** if any item remains unchecked (☐) after the final review, the result **must not** proceed to Stage 12.
