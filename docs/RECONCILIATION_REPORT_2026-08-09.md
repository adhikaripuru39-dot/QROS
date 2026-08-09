# QROS Governance Reconciliation Report

**Type:** Read-only reconciliation — no strategy, data, feature, statistical, pipeline, edge, or execution logic was modified in producing this report.
**Date:** 2026-08-09
**Repository:** `C:\Users\adhik\OneDrive\Desktop\QROS`
**Test suite at time of writing:** 82 passed · 1 failed (`tests/test_edges.py::test_false_edge_curve_fitting`)

---

## 1. Module → Handbook-Part Map

Every module below is **generic framework scaffolding**. There is **no edge-specific strategy logic** anywhere in the repository (the edge registry is empty; production status is `NOT APPROVED`). All modules were implemented **before any approved contract or edge** — none exists.

| Module | Handbook part | Inputs → Outputs | Tests | Scaffold vs edge |
| :--- | :--- | :--- | :--- | :--- |
| `governance/policy.py` | Thresholds for Parts 1–10 (ADR-001 source of truth) | none → `Policy` / `render_summary()` | `test_governance_policy` | Scaffold |
| `governance/roles.py` | Part 1 ch.1.3 | none → `Role`, `ROLE_MATRIX` | `test_schemas` | Scaffold |
| `governance/constitution.py` | Constitution Art. XI | none → `VERSION`, `AMENDMENTS` | `test_governance_policy` | Scaffold |
| `governance/decision_log.py` | Constitution Art. IX | `Decision` → persist/export | `test_governance_policy` | Scaffold |
| `schemas/data_types.py` | Part 1 ch.2 | none → 13 `FinancialDataType`, L1/L2/L3 | `test_schemas` | Scaffold |
| `schemas/vendors.py` | Part 1 ch.3 | none → 5 `VendorSpec` | `test_schemas` | Scaffold |
| `schemas/corrections.py` | Part 2 §1.6 | factors → `CorporateAction`, rollover methods | `test_schemas` | Scaffold |
| `schemas/fields.py` | Parts 5, 9 | none → HYP-01..22, EXP-01..17 authority tables | `test_schemas` | Scaffold |
| `data/quality.py` | Part 2 | OHLC df + calendar → `QualityReport` (anomalies + 8-bias) | `test_data_quality` | Scaffold |
| `data/engineering.py` | Part 3 ch.1 | tier/asset/etc → partition path, tier specs | `test_data_engineering` | Scaffold |
| `data/snapshot.py` | Part 3 ch.2.2 | df → frozen SHA-256 snapshot registry | `test_data_engineering` | Scaffold |
| `data/feature_store.py` | Part 3 ch.2.3 | feature defs → stored feature series | *(none dedicated)* | Scaffold |
| `features/transforms.py` | Part 4 ch.1–2 | price/vol arrays → fracdiff, OBI, GK, VPIN… | `test_features` | Scaffold |
| `features/validate.py` | Part 4 ch.3 | feature frame → ADF/VIF/corr report | `test_features` | Scaffold |
| `features/catalogue.py` | Part 4 ch.2 | none → 7-row taxonomy | *(none dedicated)* | Scaffold |
| `hypothesis/registry.py` | Part 5 | 22-field dict → HYP doc + SHA-256 lock | `test_hypothesis_lock` | Scaffold |
| `hypothesis/mechanics.py` | Part 6 | none → 6 documented of 15 mechanics (ADR-003) | `test_pipeline_gates` | Scaffold |
| `hypothesis/regime.py` | Part 6 ch.2 | returns → `RegimeResult` | *(none dedicated)* | Scaffold |
| `pipeline/stages.py` | Part 7 ch.1 | none → 15 `StageDef` | `test_pipeline_gates` | Scaffold |
| `pipeline/gates.py` | Part 7 ch.2 | ctx → criterion evaluations | `test_pipeline_gates` | Scaffold |
| `pipeline/state_machine.py` | Part 7 | hyp + artifacts/ctx → `ProjectRun` | `test_pipeline_gates` | Scaffold |
| `stats/sharpe.py` | Part 8 | returns → SR / DSR | `test_stats` | Scaffold |
| `stats/multiple_testing.py` | Part 8 | p-values → BH / Holm masks | `test_stats` | Scaffold |
| `stats/cpcv.py` | Part 8 | returns → CPCV paths/PBO | `test_stats` | Scaffold |
| `stats/bootstrap.py` | Part 8 ch.2 | series → stationary bootstrap / permutation | `test_stats` | Scaffold |
| `stats/timeseries.py` | Part 8/10 | series pairs → EG p, OU τ, Hurst | `test_stats` | Scaffold |
| `tracking/experiment.py` | Part 9 | EXP data → 17-field record / tracker | `test_tracking` | Scaffold |
| `edges/taxonomy.py` | Part 10 ch.1 | metrics → `EdgeClassification` | `test_edges` | Scaffold |
| `edges/audit.py` | Part 10 ch.2 | returns + optional inputs → `EdgeAudit` | `test_edges` | **Scaffold, incomplete — see §4** |
| `cli.py` | All | subcommands → exit codes | `test_cli` | Scaffold |

**Gaps observed:** `feature_store.py`, `catalogue.py`, and `regime.py` have **no dedicated tests** (covered only transitively or not at all).

---

## 2. Handbook 15-Stage → PM Macro Workflow (explicit mapping; not interchangeable)

The two schemes differ in number, ordering, and gate semantics. The handbook mandates a strict linear 15-stage gatekeeper sequence; the PM macro workflow is a coarser, reordered 8-stage programme plan. **No stage-number equivalence is claimed.** The correspondence below is a *set-membership* mapping only, and the handbook stage numbers remain the operative quality gates.

| PM macro stage | Corresponding handbook stages (Part 7) | Nature of the match |
| :--- | :--- | :--- |
| governance | *(none)* | Constitution/governance layer underpinning all 15; no handbook stage is its analogue |
| workflow / contracts | 1–3 (Idea Gen., Literature Review, Theory Formation) | Overlap only — PM defines interfaces, handbook defines idea→theory gates |
| data | 5–6 (Data Collection, Data Cleaning) | Close correspondence |
| research specification | 2–4 (Literature Review, Theory Formation, Hypothesis Creation) | PM merges handbook stages 2–4 |
| feature / experiment design | 7–8 (Feature Engineering, Exploratory Analysis) | Close correspondence |
| edge confirmation | 9–11 (Statistical Testing, Robustness, Walk-Forward) | PM merges handbook stages 9–11 |
| one complete edge module | 15 (Model Development) — *packaging*, not gate equivalence | PM treats encapsulation as a stage; handbook treats it as Stage 15 |
| independent validation | 12–13 (Replication, Documentation) | Partial — handbook validation spans 12–13 |
| controlled integration | 14–15 (Research Approval / IC, Model Development) | PM collapses the IC gate into an integration stage |

**Explicit caveats:**
- (a) Handbook stage 4 (Hypothesis Creation, 22-field SHA-256 lock) is not isolated in the PM scheme.
- (b) Handbook stage 14 (formal Investment Committee sign-off) is the *final* human gate, but PM places "controlled integration" last.
- (c) The PM workflow is a programme-manager view, **not** a substitute gate — a project that passes a PM stage has **not** satisfied the corresponding handbook gates.

---

## 3. Ratification / Approval / Complete Claims

Every claim below was authored by the automated identity **`QROS Engineering Team <qros@local>`** on 2026-08-08. There is **no named, dated human decision record** (no signature, no named signatory, no project-manager/IC record) for any of them. Per the reconciliation rules, all are therefore marked:

> **`PENDING HUMAN/PROJECT-MANAGER APPROVAL`**

| Claim location | Claim |
| :--- | :--- |
| `docs/GOVERNANCE/constitution.md` | "Version 1.0 (Founding Edition — **Ratified**)", "Ratified by the Founding Contributors, 2026-08-08" |
| `docs/DECISION_LOG.md` | **ADR-006 "Ratification of the Founding Constitution"**, status `ACCEPTED` |
| `governance/constitution.py` | `RATIFICATION_AMENDMENT` status `"RATIFIED"`; `VERSION = "…(Founding Edition — Ratified)"` |
| `docs/GOVERNANCE/bill_of_rights.md`, `bill_of_responsibilities.md`, `code_of_scientific_conduct.md`, `engineering_manifesto.md`, `founding_oath.md` | "Ratified Founding Governance", "adopted at founding" |
| `docs/HANDBOOK_INDEX.md`, `docs/PROJECT_STATE.md` | "Ratified Constitution", "complete 15-stage research framework" |
| Commit `586eda1` | "docs: ratified governance…" |

**Most consequential finding:** the Constitution document's **own source** (`QROS Constitution.docx`) is labeled *"Status: **Draft for Ratification**"* — the automated ADR-006 marked it ratified without a human act. This is the single most important outstanding governance item.

---

## 4. Failing Test — `test_false_edge_curve_fitting`

**Failure (verified by run):** the assertion
`{"curve_fitting","data_mining","coincidence","execution_mirage","capacity_bottleneck"}.issubset(diag.keys())`
fails because `audit_false_edge()` returned only **three** diagnostics — `['curve_fitting', 'data_mining', 'coincidence']`.

**Root cause — contract vs implementation mismatch.** Part 10 ch.2 requires the **five** false-edge diagnostics:

1. Curve-fitting / overfitting
2. Data mining / snooping (DSR)
3. Coincidence / luck (permutation)
4. Execution mirage (L2 spread + market impact)
5. Capacity bottleneck (<$10k vs $50M)

The implementation `audit_false_edge()` in `src/qros/edges/audit.py` makes diagnostics **4 and 5 conditional on caller-supplied optional inputs**:

- `execution_mirage` runs **only if** `execution_slippage_bps is not None` (line 101)
- `capacity_bottleneck` runs **only if** `tiny_size_pnl` **and** `institutional_size_pnl` are both given (line 116)

The test invoked only `perturbed_returns=…` (plus `n_trials=5`), so diagnostics 1–3 ran and 4–5 were silently skipped. The test's expectation (all five always present) is the *handbook-correct* contract; the implementation is the deviation. The function additionally implements a sixth, optional `structural_cointegration` diagnostic (lines 130–141) beyond the handbook's five.

**Implication:** the "5 false-edge audit" is not actually enforced as a fixed contract — its completeness depends on what the caller happens to pass. This is a **coverage defect** in the audit implementation, not merely a test bug. Correct resolutions are either:
- (a) make diagnostics 4–5 unconditional with documented defaults, or
- (b) require all five inputs in the signature so a partial audit is impossible.

**Per the reconciliation instruction, no code was changed** — this section is diagnosis only.

---

## 5. Uncommitted / Untracked Files

### Modified (tracked, not committed)
| File | Purpose | Disposition |
| :--- | :--- | :--- |
| `src/qros/data/quality.py` | 1-line fix `.tz` → `.dt.tz` (pandas 3.0 dropped the Series attribute); required by `test_utc_timezone_normalization` | **Safe to commit** (after suite is green) |

### Untracked (new)
| File | Purpose | Disposition |
| :--- | :--- | :--- |
| `tests/conftest.py` | Shared deterministic fixtures (OHLC, returns, HYP/EXP specs, snapshot registry) | **Safe to commit** |
| `tests/test_cli.py` | CLI smoke tests | **Safe to commit** |
| `tests/test_data_engineering.py` | Snapshot/partition/tier tests | **Safe to commit** |
| `tests/test_data_quality.py` | Anomaly/bias tests | **Safe to commit** |
| `tests/test_edges.py` | Edge classification + false-edge audit tests | **Needs review** — contains the failing `test_false_edge_curve_fitting` (§4) |
| `tests/test_features.py` | Transforms + ADF/VIF tests | **Safe to commit** |
| `tests/test_governance_policy.py` | Policy literals, roles, constitution, ADR | **Safe to commit** |
| `tests/test_hypothesis_lock.py` | HYP registry immutability | **Safe to commit** |
| `tests/test_pipeline_gates.py` | 15-stage state machine | **Safe to commit** |
| `tests/test_schemas.py` | Taxonomy / fields / vendors | **Safe to commit** |
| `tests/test_stats.py` | DSR / FDR / FWER / CPCV / bootstrap | **Safe to commit** |
| `tests/test_tracking.py` | EXP record + tracker | **Safe to commit** |

**Also observed:** `tests/__init__.py` is committed but the entire test suite is not — the "test suite" was never committed as a unit. Git-ignored runtime/derived dirs (`_extracted/`, `registry/`, `.claude/`) are intentionally excluded and carry no reconciliation risk.

---

## Recommended Action

1. Fix/align the audit contract (§4) so all five false-edge diagnostics are always enforced.
2. Commit the `data/quality.py` fix plus the 11 test files and `conftest.py` together so the suite is in-repo and green.
3. Resolve the ratification claims (§3) with an actual named, dated human/project-manager decision record before any "ratified" wording is relied upon.
