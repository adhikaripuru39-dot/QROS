# QROS - Stage 7 Research Pipeline Rule Map

Specification-only. Grounded in Master Handbook Part 7 (15-stage linear workflow). Gates and thresholds taken verbatim; **no shortcuts, no retroactive relaxation** (Part 7 §2; ADR-001).

**MAND** = mandatory; **BLOCK** = what a failure halts.

---

## 1. Stage order and dependencies
- **Rule P7-01:** Research is a **strictly linear** 15-stage workflow (Part 7 §1). A stage may begin only when the prior stage's gate has passed and been signed off.

| # | Stage | Required output (artifact) | Quality gate / sign-off |
| :- | :--- | :--- | :--- |
| 1 | Idea Generation | Idea Note & Mechanism Description | Peer review (QR team) |
| 2 | Literature Review | Annotated bibliography & academic matrix | Novelty vs published work |
| 3 | Theory Formation | Economic/behavioral mechanism spec | Head of Research approval |
| 4 | Hypothesis Creation | Registered 22-field HYP, locked | SHA-256 lock & registration |
| 5 | Data Collection | Acquisition request & schema spec | Data Engineer lineage audit |
| 6 | Data Cleaning | Cleansed snapshot & quality metrics | Zero bad-tick + timestamp audit |
| 7 | Feature Engineering | Feature store extraction & stationarity | ADF p < 0.05 (all features) |
| 8 | Exploratory Analysis | EDA notebook & correlation matrix | VIF < 10.0 (multicollinearity) |
| 9 | Statistical Testing | In-sample hypothesis test report | t-stat > 3.0, p < 0.001 |
| 10 | Robustness Testing | Parameter sensitivity & stress suite | Stable across ±50% parameter shift |
| 11 | Walk-Forward Validation | OOS walk-forward performance matrix | OOS Sharpe > 2.0, MaxDD < 15% |
| 12 | Replication | Independent code-base replication | Secondary QR match > 99.9% |
| 13 | Documentation | Final research monograph & code manual | Peer-review sign-off |
| 14 | Research Approval | Investment Committee presentation | Formal IC sign-off (Head + Risk) |
| 15 | Model Development | Production model architecture spec | Hand-off to Quant Dev |

- **MAND:** Stages run in order; Stage N+1 depends on Stage N sign-off.
- **Source:** Part 7 §1.
- **BLOCK:** Skipping or reordering stages blocks the research and halts the workflow.

## 2. Required approvals and sign-offs
- **Rule P7-02:** Transitioning between stages requires **formal review and sign-off** from the **Lead Statistician and Head of Research** (or the named gate owner) (Part 7 §1 mandate).
- **MAND:** Each stage records its sign-off authority (QR team, Head of Research, Data Engineer, Lead Statistician, Investment Committee + Risk).
- **Source:** Part 7 §1; Part 1 §1.3 roles.
- **BLOCK:** Missing sign-off blocks progression to the next stage.

## 3. Gate failures and rollback conditions
- **Rule P7-03:** IF ANY STAGE violates its quality gate, the project is **immediately halted**; the reason is documented in the Experiment Registry; the hypothesis is marked **REJECTED** or returned to **Stage 3** (Theory Formation) for re-formulation (Part 7 §2). **Retroactive threshold relaxation is prohibited** (Part 7 §2; ADR-001).
- **MAND:** Failure is logged; rollback target is defined (Stage 3 re-formulation); no gate is lowered to force a pass.
- **Source:** Part 7 §2.
- **BLOCK:** A gate failure halts the project; un-documented or un-logged failure is escalated.

## 4. Research execution boundaries
- **Rule P7-04:** Research execution (data collection, cleaning, features, statistical testing, robustness, walk-forward) is **governed within the pipeline only** (Stages 5-12). 
- **MAND:** Backtesting/walk-forward is allowed **only** at the governed validation stages (9-11) for the registered hypothesis; **no** strategy implementation, **no** ungoverned backtest, **no** execution.
- **Source:** Part 7 §1; Charter §1, §5.
- **BLOCK:** Any out-of-pipeline strategy or execution work halts the research.

## 5. Allowed artifacts per stage
- **Rule P7-05:** Each stage may produce only its documented artifact (the "Required output" column of §1): idea notes, bibliographies, mechanism specs, HYP documents, data/schema specs, cleaned snapshots, feature/EDA artifacts, test reports, stress suites, walk-forward matrices, replication code, monograph, IC presentation, production architecture spec.
- **MAND:** Artifacts are specification/research outputs — never production trading code, never execution logic.
- **Source:** Part 7 §1.
- **BLOCK:** Producing a disallowed artifact (e.g. execution code) at any stage halts the project.

## 6. What blocks progression to validation or approval
- **Rule P7-06:** Progression to validation (Stage 11) and approval (Stage 14) is **blocked** unless **all** prior gates passed with sign-off and zero violations (P7-01..P7-05). Approval additionally requires: Stage 12 replication match > 99.9%, Stage 13 monograph peer-review, and Stage 14 formal IC sign-off (Head + Risk).
- **MAND:** No hypothesis reaches validation/approval without the complete chain; blockers are logged.
- **Source:** Part 7 §1 (Stages 11-14), §2.
- **BLOCK:** Any unmet gate blocks validation and/or research approval.

---

## Mandatory stage gates (summary)
All 15 gates are mandatory. Key hard thresholds: Stage 7 ADF p<0.05 · Stage 8 VIF<10.0 · Stage 9 t-stat>3.0 / p<0.001 · Stage 10 stable ±50% · Stage 11 OOS Sharpe>2.0 / MaxDD<15% · Stage 12 replication >99.9%.

## How a failed gate is handled (summary)
Halt immediately → document reason in Experiment Registry → mark hypothesis REJECTED or return to Stage 3 for re-formulation → never relax a threshold.

## Artifacts that must exist before Stage 8 begins
1. Approved Stage 7 pipeline-rule set (this map) + sign-off.
2. The governed 15-stage workflow confirmed (order, gates, sign-offs).
3. Approved, registered hypotheses (Stage 5/6) and approved features (Stage 4) queued into the pipeline.
4. Gate-failure / rollback protocol in place.
5. Decision-log entry recording Stage 7 approval.
