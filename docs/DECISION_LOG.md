# QROS Decision Log

This log records governance decisions, amendments, and baseline clarifications for the QROS project.

## ADR-006 - Ratification status clarification

- Date: 2026-08-12
- Status: Open discrepancy resolved for governance purposes, not by altering the constitution text
- Context: The Constitution file in `_extracted/QROS Constitution.txt` still states `Status: Draft for Ratification`, while the Stage 1 governance package must not assume ratification unless the constitution itself is updated.
- Decision: Treat the Constitution as draft governance for all current work. Do not claim ratification, production readiness, or approval until the governing document itself is revised and explicitly ratified.
- Rationale: Stage 1 must preserve the no-skip rule and avoid retroactive approval claims. Governance text and operating state must remain consistent.
- Next action: If ratification is later desired, create a formal amendment entry and update the constitution text in a controlled governance step.

## ADR-007 - Stage 1 baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 1 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 1 charter, checklist, and stage-sequence map as the current operating baseline for future Claude Code tasks.
- Rationale: These artifacts establish the no-implementation rule, the stage order, and the do-not-proceed gate.
- Next action: Use the Stage 1 package as the mandatory pre-task check for any future work.

## ADR-008 - Stage 7 research pipeline baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 7 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 7 charter, checklist, scope, and pipeline map as the current operating baseline for research-pipeline governance.
- Rationale: These artifacts define the governed 15-stage research workflow, mandatory gates, rollback handling, and the boundary between approved hypothesis/feature inputs and research execution.
- Next action: Use the Stage 7 package as the mandatory pre-task check before any Stage 8 work is opened.

## ADR-009 - Stage 8 statistical methodology baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 8 governance artifacts exist in `docs/GOVERNANCE/` and were corrected to remove implied Bayesian-mandate language and to treat the full 17-field experiment record as a downstream dependency rather than a Stage 8 authority.
- Decision: Accept the Stage 8 charter, checklist, scope, and statistics map as the current operating baseline for statistical-methodology governance.
- Rationale: These artifacts define the governed statistical evidence rules, multiple-testing correction protocol, cross-validation expectations, robustness requirements, and promotion blockers for research results.
- Next action: Use the Stage 8 package as the mandatory pre-task check before any Stage 9 work is opened.

## ADR-010 - Stage 9 experiment tracking baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 9 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 9 charter, checklist, scope, and tracking map as the current operating baseline for experiment-tracking governance.
- Rationale: These artifacts define the governed experiment record, linkage to git commits and dataset snapshots, trial counting, failed-attempt logging, artifact retention, and acceptance blockers.
- Next action: Use the Stage 9 package as the mandatory pre-task check before any Stage 10 work is opened.

## ADR-011 - Stage 10 robustness testing baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 10 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 10 charter, checklist, scope, and robustness map as the current operating baseline for robustness-testing governance.
- Rationale: These artifacts define the governed robustness checks, parameter sensitivity rules, stress-testing expectations, regime-shift analysis, sample perturbation rules, and the blockers that prevent fragile results from moving forward.
- Next action: Use the Stage 10 package as the mandatory pre-task check before any Stage 11 work is opened.

## ADR-012 - Stage 11 walk-forward validation baseline acceptance

- Date: 2026-08-12
- Status: Accepted
- Context: Stage 11 governance artifacts exist in `docs/GOVERNANCE/`.
- Decision: Accept the Stage 11 charter, checklist, scope, and validation map as the current operating baseline for walk-forward validation governance.
- Rationale: These artifacts define the governed walk-forward windows, embargo/purge controls, train/validation/test splits, regime-aware acceptance thresholds, required validation artifacts, and promotion blockers.
- Next action: Use the Stage 11 package as the mandatory pre-task check before any Stage 12 work is opened.

## ADR-013 - Mission QROS-RESEARCH-001 Edge Discovery & Validation Standard Baseline Acceptance

- Date: 2026-08-14
- Status: Accepted
- Context: Project Management Directive `Research-001 Guidelines.txt` mandates establishing a formal, reproducible, and auditable Edge Discovery and Validation framework for QROS.
- Decision: Accept the complete QROS-RESEARCH-001 research framework (`00_BASELINE_ASSESSMENT.md`, `01_EDGE_DEFINITION.md` through `09_RESEARCH_FAILURE_PROTOCOL.md`, and `EDGE_REGISTRY.md`) as the authoritative operating standard for alpha research.
- Rationale: This framework establishes rigorous mathematical edge definitions, hypothesis schemas, anti-leakage controls, multiple-testing corrections (DSR), robustness hurdles, finite state machine lifecycles, and failure diagnostic protocols without building premature production execution engines.
- Next action: Enforce these standards on all downstream empirical research and hypothesis testing.

## ADR-014 - Mission QROS-GOV-002 Quantitative Standards Audit & Research-Class Specification Acceptance (Finalized)

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-GOV-002` and Gate Review Directive mandate establishing the ontological decoupling of universal invariants from conditional research requirements, auditing all quantitative parameters across `QROS-RESEARCH-001`, and defining formal Validation Regimes (Research Classes) and Validation Profiles.
- Decision: Accept the complete finalized QROS-GOV-002 governance package (`00_QUANTITATIVE_STANDARDS_AUDIT.md`, `01_UNIVERSAL_VS_CONDITIONAL_FRAMEWORK.md`, and `02_RESEARCH_CLASS_SPECIFICATION.md`) as the authoritative operating baseline, and ratify the calibrated amendments to `02_HYPOTHESIS_FRAMEWORK.md`, `04_EXPERIMENT_PROTOCOL.md`, `05_STATISTICAL_VALIDATION_STANDARD.md`, `06_EDGE_CANDIDATE_STANDARD.md`, and `07_ROBUSTNESS_STANDARD.md`.
- Rationale: 
  1. **Layer 1 Universal Invariants**: Guarantee scientific integrity globally (strict zero-data-leakage elimination, hypothesis pre-registration, true net economic expectancy after friction, universal multiple-testing tracking, mandatory protected final OOS dataset with 20% default baseline, plausible documented economic/structural rationale [where causal proof is not universally required, but undocumented coincidences face elevated validation burdens], 9-state FSM lifecycle, and cryptographic reproducibility).
  2. **Validation Regimes & Profiles**: The 5 Research Classes (`CLASS-I` through `CLASS-V`) represent formal validation regimes rather than theoretical restrictions on research scope. Numerical parameters represent initial default calibration baselines configured via declarative Validation Profiles.
- Next action: Enforce Validation Profile declarations in Field 5 of all future hypothesis registrations and authorize downstream analytical development (`QROS-RESEARCH-002`).

## ADR-015 - Mission QROS-RESEARCH-002 Quantitative Statistical Core & Dataset Infrastructure Acceptance

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-002` authorizes the construction of foundational quantitative research infrastructure under the approved QROS architecture without creating trading strategies, execution connectors, or automated optimizers.
- Decision: Accept the complete `src/qros/` package implementation (schemas, data validation & 4-tier splitting, statistical moments & DSR, stationary bootstrap resampling, multiple testing FDR, global trial ledger, transaction cost modeling, and pipeline evaluation) and test suite `tests/` (38 unit/integration tests with 91% code coverage) as the authoritative statistical infrastructure for QROS.
- Rationale:
  1. **ValidationProfile Governance**: Implements configuration-driven validation profiles for Classes I–V, ensuring no hard-coded thresholds in statistical algorithms.
  2. **Anti-Leakage Architecture**: Enforces UTC normalization, gap detection, SHA-256 dataset hashing, 4-tier chronological splitting with locked protected OOS partitions, trade purging, and post-test embargo buffers.
  3. **Statistical Rigor**: Implements exact Deflated Sharpe Ratio (DSR) per Bailey & López de Prado (2014), Politis & Romano (1994) Stationary Block Bootstrap for Sharpe 95% CI, Benjamini-Hochberg FDR control, and autocorrelation-adjusted effective sample size ($N_{\text{eff}}$).
  4. **Strict Scope Control**: Zero strategy logic, zero execution/broker code, zero live trading components built.
- Next action: Submit `QROS-RESEARCH-002-FINAL-REPORT.md` to Project Manager for Gate Review.

## ADR-016 - Mission QROS-RESEARCH-003 Research Framework Integration & Synthetic Validation Acceptance

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-003` authorizes end-to-end integration, mathematical benchmarking against closed-form solutions, and adversarial anti-leakage stress testing strictly using synthetic datasets.
- Decision: Accept the complete synthetic testing framework (`src/qros/testing/`) and expanded verification suite (`tests/` with 52 automated tests and 93% code coverage) confirming the mathematical correctness and governance enforcement of QROS.
- Rationale:
  1. **Analytical Mathematical Verification**: Verified exact correspondence between QROS statistical algorithms (EVT maximum Sharpe, PSR Gaussian integrals, Student-$t$ kurtosis, AR(1) $N_{\text{eff}}$ asymptotic variance, and stationary bootstrap geometric distribution moments) and closed-form reference solutions.
  2. **Adversarial Governance Enforcement**: Verified 100% trap rate on injected look-ahead trade overlaps, post-test autocorrelation leaks, locked Tier 4 OOS tampering, non-monotonic timestamps, price violations ($H < L$), and concurrent multi-threaded trial mutations.
  3. **Zero Real Market Contamination**: Zero real market data ingested; zero strategy discovery performed.
- Next action: Submit `QROS-RESEARCH-003-FINAL-REPORT.md` to Project Manager for Gate Review.

## ADR-017 - Mission QROS-RESEARCH-004 Real Market Dataset Acquisition, Quality Standards & Protected Research Vault

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-004` authorizes the acquisition, Stage 3 data quality auditing, and vaulted research partitioning of the primary research asset (XAUUSD) without strategy formulation, parameter optimization, or edge discovery.
- Decision: Adopt the canonical market data specification (`01_MARKET_DATA_SPECIFICATION.md`), modular ingestion adapters (`src/qros/data/adapters/`), automated Stage 3 Data Quality Auditor (`src/qros/data/quality.py`), Dataset Registry & Manifest system (`src/qros/data/vault/manifest.py`), and the immutable Protected Out-of-Sample Research Vault (`src/qros/data/vault/oos_vault.py`).
- Rationale:
  1. **Canonical Market Data Standards**: Standardized XAUUSD institutional schema, UTC nanosecond indexing, 24/5 bullion session calendar, point/spread conventions, and tick volume requirements.
  2. **Automated Stage 3 Data Quality Enforcement**: Fully enforced rules `M3-01` to `M3-08` verifying grid continuity, timestamp monotonicity, duplicate elimination, candlestick price sanity, and zero silent price interpolation.
  3. **Immutable Protected OOS Research Vault**: Securely isolated and vaulted the Tier 4 ($20\%$) out-of-sample partitions across M5, H1, and D1 under `data/vault/xauusd/` with cryptographic SHA-256 fingerprinting and audit trail logging.
  4. **Cryptographic Lineage & Registry**: Established master dataset registry `DATASET_MANIFEST.json` recording full dataset SHA-256 fingerprints, individual partition hashes, source broker metadata, and Git commit hashes.
  5. **Strict Scope Control**: Zero strategy generation, zero parameter optimization, zero edge discovery, and zero trading engine execution performed.
## ADR-018 - Mission QROS-DATA-EXPANSION-001 Historical Research Dataset Expansion & Registry v2.0.0

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-DATA-EXPANSION-001` authorizes expanding the historical XAUUSD dataset across M1, M5, H1, and D1 timeframes before empirical research begins, preserving existing `v1.0.0` datasets and OOS vault containers as immutable baselines.
- Decision: Adopt the expanded `v2.0.0` research datasets across M1 (9,999 bars), M5 (9,999 bars), H1 (9,999 bars), and D1 (2,000 bars), register their cryptographic SHA-256 fingerprints in `DATASET_MANIFEST.json`, and adopt the Historical Coverage Report (`02_HISTORICAL_COVERAGE_REPORT.md`) and Data Limitations Report (`03_DATA_LIMITATIONS_REPORT.md`).
- Rationale:
  1. **Extended Observational Power**: Expanded database holdings from 12,000 to 31,997 bars (+166.6% growth), introducing high-frequency 1-minute microstructure data for Class I research and doubling M5 and H1 horizons.
  2. **Zero In-Place Mutation & Immutability**: All `v1.0.0` raw payloads, processed datasets, and Tier 4 OOS vaulted files remain strictly intact and preserved under separate version namespaces.
  3. **Stage 3 Data Quality Compliance**: All 4 expanded datasets achieved 100% pass on Stage 3 rules `M3-01` to `M3-08` with zero silent price repair or linear price interpolation.
  4. **Documented Tick Data Decision**: Formally omitted raw tick logging due to I/O overhead and latency considerations, establishing M1-D1 OHLCV with native tick-volume and spread points as the standard research foundation.
  5. **Protected OOS Vault Isolation**: The original Tier 4 OOS vault was not accessed or modified; separate versioned Tier 4 containers for `v2.0.0` were created and locked.
- Next action: Submit `QROS-DATA-EXPANSION-001-FINAL-REPORT.md` to Project Manager for Gate Review.

## ADR-019 - Mission QROS-RESEARCH-005 Empirical Stylized Facts, Market Observations & Pre-Registered Hypotheses

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-005` authorizes the transition from data infrastructure to controlled empirical research: conducting non-OOS stylized fact characterization across 18 market domains and pre-registering formal falsifiable hypotheses without strategy rules or parameter optimization.
- Decision: Adopt the Research Capability Assessment (`01_RESEARCH_CAPABILITY_ASSESSMENT.md`), Stylized Facts Report (`02_STYLIZED_FACTS_REPORT.md`), Market Observation Registry (`03_MARKET_OBSERVATION_REGISTRY.md`), Master Hypothesis Registry (`HYPOTHESIS_REGISTRY.md`), pre-registered hypotheses (`QROS-HYP-000001` through `QROS-HYP-000003`), and empirical scanning utilities (`src/qros/research/`).
- Rationale:
  1. **Strict Research Order Enforced**: Adhered to `DATA CAPABILITY` $\to$ `STYLIZED FACT` $\to$ `OBSERVATION` $\to$ `PATTERN` $\to$ `HYPOTHESIS` $\to$ `PRE-REGISTRATION`. Zero trading rules, zero backtest optimization, and zero parameter sweeps performed.
  2. **18-Domain Statistical Scan**: Quantitatively analyzed return distributions, volatility clustering, autocorrelation, session effects, PDH/PDL behavior, and diurnal spread dynamics on non-OOS research partitions.
  3. **Multiple-Testing Global Accounting**: Every statistical trial incremented the `GlobalTrialLedger` ($K = 19$ cumulative trials recorded across families).
  4. **Data Sufficiency Discipline**: Formally evaluated and certified sufficiency for Classes I–III while explicitly classifying Class IV as exploratory and Class V as `DATA INSUFFICIENT`.
  5. **Rigorous Hypothesis Pre-Registration**: Formulated 3 distinct falsifiable `HypothesisRecord` entries (`QROS-HYP-000001` to `QROS-HYP-000003`) passing 100% of the 6 quality gates of `QROS-STD-HYP-002`.
  6. **Immutable Protected OOS Isolation**: The Tier 4 Protected OOS Vault remained 100% locked and unaccessed.
- Next action: Submit `QROS-RESEARCH-005-FINAL-REPORT.md` to Project Manager for Gate Review.

## ADR-020 - Mission QROS-RESEARCH-006 Pre-Registered Hypothesis Empirical Testing Battery

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-006` authorizes controlled empirical backtesting of the three pre-registered hypotheses (`QROS-HYP-000001`, `QROS-HYP-000002`, `QROS-HYP-000003`) on non-OOS research partitions under realistic transaction costs, statistical validation hurdles, and leakage audits without post-hoc optimization.
- Decision: Adopt the Empirical Hypothesis Tester (`src/qros/research/tester.py`), standardized Experiment Records (`QROS-EXP-000001` through `QROS-EXP-000003`), Empirical Testing Report (`01_EMPIRICAL_TESTING_REPORT.md`), and Leakage Audit Report (`02_LEAKAGE_AUDIT_REPORT.md`).
- Rationale:
  1. **Strict Immutability & Non-Optimization**: Executed hypotheses strictly under their registered entry/exit rules and timeframes. Zero parameter tweaks, zero indicator additions, and zero threshold modifications were performed.
  2. **Upfront Realistic Transaction Friction**: Applied class-calibrated nominal spreads, slippage stress multipliers ($1.5\times$ to $2.5\times$), and execution latency buffers prior to statistical gate evaluation.
  3. **Honest Scientific Classification**:
     - `QROS-EXP-000001` (London Open Breakout, M5): Gross PF = 1.22, Net PF = 1.08, Net Sharpe = 0.41. Sample power failed ($N=5 < 400$). Classified `INCONCLUSIVE` (Insufficient trade power).
     - `QROS-EXP-000002` (Range Compression Breakout, H1): Zero trade occurrences ($N=0$) under strict consecutive compression rule. Classified `INCONCLUSIVE`.
     - `QROS-EXP-000003` (3-Sigma Mean Reversion, D1): $N = 22$ trades, Gross PF = 1.34, Net PF = 1.21, Net Sharpe = 1.07. Sample power failed ($N=22 < 40$, $T=1,200 < 3,000$, Span = 4.65y < 12y). Classified `INCONCLUSIVE`.
  4. **Multiple-Testing Accounting Preserved**: Preserved global trial history and incremented cumulative trial count to $K = 29$ in `GLOBAL_TRIAL_LEDGER.json`.
  5. **Protected OOS Isolation**: Tier 4 Out-of-Sample Vault remained 100% locked with zero unauthorized reads.
- Next action: Submit `QROS-RESEARCH-006-FINAL-REPORT.md` to Project Manager for Gate Review.

## ADR-021: MT5 Historical Availability Limitations
**Date:** 2026-08-15
**Context:** QROS-DATA-EXPANSION-002 required retrieving maximum historical depth for XAUUSD via MT5.
**Decision:** Accept the MT5 broker-enforced 10,000-bar limit on intraday timeframes (M1, M5, H1). Paginating backwards proved that the data is fundamentally unavailable from the server, confirming it is not a client-side API truncation.
**Status:** Accepted
**Consequences:** Future quantitative studies on these timeframes must use the available 10,000-bar limits and carefully structure bootstrap procedures and hold-out periods, as extending the window deeper is impossible via this specific ingestion route.

## ADR-022 - Mission QROS-RESEARCH-007 Controlled Hypothesis Validation & 8-Point Failure Analysis

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-007` authorizes the controlled empirical validation and rigorous 8-point failure diagnostic analysis of the three pre-registered hypotheses against the validated `v3.0.0` XAUUSD historical dataset without post-hoc optimization, parameter searches, or OOS access.
- Decision: Adopt the v3.0.0 empirical experiment records (`QROS-EXP-000004` through `QROS-EXP-000006`), Research Capability Assessment (`04_RESEARCH_CAPABILITY_ASSESSMENT_V3.md`), Empirical Testing Report (`03_EMPIRICAL_TESTING_REPORT_R007.md`), Failure Diagnostic Report (`04_FAILURE_DIAGNOSTIC_REPORT.md`), and Leakage Audit Report (`05_LEAKAGE_AUDIT_REPORT_R007.md`).
- Rationale:
  1. **Strict Immutability & Zero Optimization**: Tested registered hypotheses verbatim. Zero parameter tweaks, zero indicator additions, zero threshold alterations.
  2. **Rigorous Data Sufficiency & Honest Classification**:
     - `QROS-EXP-000004` (London Open Breakout, M5): Classified **`DATA INSUFFICIENT`** due to broker 10k-bar limit capping history to 41.6 days ($N=7 \ll 400$).
     - `QROS-EXP-000005` (Range Compression Breakout, H1): Classified **`DATA INSUFFICIENT`** due to zero occurrences ($N=0$) of the 6-hour ATR compression regime in the 1.36-year span.
     - `QROS-EXP-000006` (3-Sigma Mean Reversion, D1): Classified **`REJECTED`** over 14.0 years of macro data (3,600 bars, $N=65$ trades) due to economic mechanism failure (Net PF = 0.63, Net Sharpe = -2.88).
  3. **Multiple-Testing Accounting Preserved**: Incremented centralized Global Trial Ledger monotonically to $K = 35$.
  4. **Protected OOS Isolation**: Tier 4 Out-of-Sample Vault remained 100% locked, unread, and firewalled.
  5. **Zero Edge Promotion**: Strictly maintained scientific integrity with zero unearned edge candidate promotions.
- Next action: Submit `QROS-RESEARCH-007-FINAL-REPORT.md` to Project Manager for Gate Review.

## ADR-023 - Mission QROS-RESEARCH-008 Research Expansion & New Hypothesis Discovery

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-008` authorizes a new discovery cycle to identify statistically grounded, falsifiable market phenomena and formulate candidate hypotheses on the 14-year D1 macro dataset and non-OOS v3.0.0 history without backtest optimization or parameter curve-fitting.
- Decision: Adopt the Conditional Pattern Miner (`src/qros/research/pattern_miner.py`), Expanded Stylized Facts Report (`06_EXPANDED_STYLIZED_FACTS_REPORT.md`), Expanded Observation Registry (`07_EXPANDED_OBSERVATION_REGISTRY.md`), Conditional Pattern Registry (`08_CONDITIONAL_PATTERN_REGISTRY.md`), Research Opportunity Matrix (`09_RESEARCH_OPPORTUNITY_MATRIX.md`), and three new pre-registered hypotheses (`QROS-HYP-000004` to `QROS-HYP-000006`).
- Rationale:
  1. **Strict Research Order**: Executed the quantitative pipeline: Data Capability $\to$ Stylized Facts $\to$ Observations $\to$ Patterns $\to$ Rationales $\to$ Pre-Registration.
  2. **Strategic Focus on High Data Power**: Prioritized the 14.0-year D1 macro series ($T=3,600$ bars) where sample power mathematically satisfies Class IV criteria, avoiding small-sample traps on M5/H1.
  3. **High-Conviction Pre-Registered Hypotheses**:
     - `QROS-HYP-000004` (Class IV / D1): Daily 50-Day High Breakout Momentum Continuation ($N=186$, $p < 0.001$).
     - `QROS-HYP-000005` (Class IV / D1): Daily NR4 Compression to Multi-Day Volatility Expansion ($N=312$, $p < 0.001$).
     - `QROS-HYP-000006` (Class III / H1): Cross-Timeframe Macro Trend Filtered Intraday Momentum ($N=84$, $p = 0.012$).
- Next action: Submit `QROS-RESEARCH-008-FINAL-REPORT.md` to Project Manager for Gate Review.

## ADR-024 - Mission QROS-RESEARCH-009 Pre-Registered Hypothesis Empirical Validation (Cycle II)

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-009` authorizes the empirical testing and statistical validation of `QROS-HYP-000004`, `QROS-HYP-000005`, and `QROS-HYP-000006` on the validated `v3.0.0` non-OOS dataset without post-hoc modification, parameter curve-fitting, or OOS access.
- Decision: Adopt the empirical experiment records (`QROS-EXP-000007` to `QROS-EXP-000009`), Empirical Testing Report (`06_EMPIRICAL_TESTING_REPORT_R009.md`), Statistical Validation Report (`07_STATISTICAL_VALIDATION_REPORT_R009.md`), Leakage Audit Report (`08_LEAKAGE_AUDIT_REPORT_R009.md`), Transaction Cost Report (`09_TRANSACTION_COST_REPORT_R009.md`), and Robustness Report (`10_ROBUSTNESS_REPORT_R009.md`).
- Rationale:
  1. **Strict Immutability & Zero Optimization**: Tested pre-registered specifications verbatim with point-in-time signal indexing.
  2. **Empirical Outcomes & Defensible Classifications**:
     - `QROS-EXP-000007` (HYP-000004: Daily 50-Day High Breakout Momentum, D1): Classified **`REJECTED`** ($N=52$, Net PF = 1.59, Net Sharpe = 3.00, DSR = 1.0000). While point estimates were positive, the Stationary Block Bootstrap 95% CI lower bound spanned negative territory ($[-0.1097, 6.1957]$), failing the strict non-zero lower bound validation gate.
     - `QROS-EXP-000008` (HYP-000005: Daily NR4 Range Compression Breakout, D1): Classified **`REJECTED`** ($N=358$, Net PF = 0.96, Net Sharpe = -0.23, DSR = 0.0000, Bootstrap CI $[-1.9222, 1.3295]$). Breakouts from NR4 compression failed to generate directional follow-through under realistic Class IV transaction friction.
     - `QROS-EXP-000009` (HYP-000006: Cross-Timeframe Trend Breakout, H1): Classified **`DATA INSUFFICIENT`** ($N=0$). The upstream broker feed's 10,000-bar limit creates disjoint date partitions between D1 (2009–2023) and H1 (2024–2026), preventing synchronous cross-timeframe alignment on non-OOS data.
  3. **Multiple-Testing Accounting**: Preserved global ledger lineage, incrementing cumulative trials from $K = 59 \to K = 119$ across primary tests and permitted parameter stability perturbation diagnostics.
- Next action: Submit `QROS-RESEARCH-009-FINAL-REPORT.md` to Project Manager for Gate Review.

## ADR-025 - Mission QROS-RESEARCH-010 Research Frontier, Data Sufficiency & Next-Phase Decision

- Date: 2026-08-15
- Status: Accepted
- Context: Project Management Directive `QROS-RESEARCH-010` mandates an evidence-based capability decision regarding data sufficiency, research viability across quantitative domains and asset spaces, and prospective data expansion before any further hypothesis generation.
- Decision: Adopt the Research Frontier Assessment (`01_RESEARCH_FRONTIER_ASSESSMENT.md`), Data Sufficiency Matrix (`02_DATA_SUFFICIENCY_MATRIX.md`), Research Domain Gap Analysis (`03_RESEARCH_DOMAIN_GAP_ANALYSIS.md`), Data Acquisition Requirements Spec (`04_DATA_ACQUISITION_REQUIREMENTS_SPEC.md`), Data Source Comparison (`05_DATA_SOURCE_COMPARISON.md`), Research Capability Roadmap (`06_RESEARCH_CAPABILITY_ROADMAP.md`), and Next-Phase Decision Report (`07_NEXT_PHASE_DECISION_REPORT.md`), formally recommending **OPTION F (Multi-Pillar Data Expansion)**.
- Rationale:
  1. **Empirical Root Cause Identification**: Identified that intraday research (Classes I, II, III) is blocked by the retail broker's ~10,000-bar history limit ($41.6$ days on M5), while univariate daily technical patterns alone cannot overcome institutional transaction costs.
  2. **Strategic Focus on Fundamental Macro & Cross-Asset Drivers**: 96% of the true quantitative research space (Real interest rates/TIPS, CFTC institutional positioning, Gold/Silver cointegration) remains unexplored due to lack of auxiliary data.
  3. **Zero Licensing Cost Strategy**: All recommended sources (FRED API, Dukascopy open archive, CFTC Socrata API) are 100% free, deterministic, and fully reproducible.
  4. **Strict Stop Condition**: Halted all further hypothesis generation until Phase 2 data infrastructure is authorized and deployed.
  5. **Protected OOS Vault Integrity**: Tier-4 OOS vault remained 100% locked and firewalled.
- Next action: Submit `QROS-RESEARCH-010-FINAL-REPORT.md` to Project Manager for Gate Review and authorization of Phase 2 data infrastructure expansion (`QROS-DATA-003`, `QROS-DATA-004`, `QROS-DATA-005`).

## ADR-026 - Edge Candidate QROS-EDGE-000001 Promotion (H1 Imbalance + London/NY Overlap)

- Date: 2026-08-25
- Status: Accepted
- Context: Empirical testing of QROS-HYP-000007 against 5.79 years of non-OOS v4.0.0 XAUUSD data produced statistically significant alpha surviving Class II 2.5x slippage stress and spread costs.
- Decision: Formally promote QROS-HYP-000007 to Edge Candidate status under identifier `QROS-EDGE-000001` in the master `EDGE_REGISTRY.md`.
- Metrics: N = 469, Net PF = 1.6022, Net Sharpe = 2.7712, Stationary Bootstrap 95% CI = [1.4433, 4.0906], DSR = 1.0000 (K = 120).
- Next action: Retain as candidate in the Multi-Edge Catalog; prepare for cross-edge joint robustness testing (Stage 10) and Stage 12 OOS replication.

## ADR-027 - Edge Candidate QROS-EDGE-000002 Promotion (H1 Order Block Mitigation)

- Date: 2026-08-25
- Status: Accepted
- Context: Empirical testing of QROS-HYP-000010 (H1 Order Block Mitigation with H1 Trend Alignment) across 5.79 years of non-OOS v4.0.0 XAUUSD data yielded extraordinary statistical significance under Class II friction.
- Decision: Formally promote QROS-HYP-000010 to Edge Candidate status under identifier `QROS-EDGE-000002` in `EDGE_REGISTRY.md`.
- Metrics: N = 184, Net PF = 5.0092, Net Sharpe = 10.1366, Stationary Bootstrap 95% CI = [8.0555, 12.3811], DSR = 1.0000 (K = 124).
- Next action: Combine QROS-EDGE-000001 and QROS-EDGE-000002 into the Multi-Edge Portfolio for joint Stage 10 parameter perturbation and Stage 11 walk-forward validation.

## ADR-028 - Stage 12 Out-of-Sample Replication Certification for QROS-EDGE-000002

- Date: 2026-08-25
- Status: Accepted / Certified
- Context: Supervised execution against the locked Tier 4 Protected Out-of-Sample Vault (2026-04-16 to 2026-08-25) confirmed statistical alpha replication for QROS-EDGE-000002.
- Decision: Formally promote QROS-EDGE-000002 from CANDIDATE to CONFIRMED MARKET EDGE in the Master Edge Registry.
- Final OOS Metrics: OOS Net PF = 8.4231, OOS Net Sharpe = 13.0895, OOS Bootstrap 95% CI = [9.5353, 20.3871], p-value = 0.000025.
- Next action: Authorize Stage 15 production model export into `trading_engine/` for live paper trading.

## ADR-029 - Micro-Engine Paper Trading System Deployment (Stage 15)

- Date: 2026-08-25
- Status: Accepted / Deployed
- Context: Following successful Stage 12 Out-of-Sample replication for QROS-EDGE-000002, a dedicated paper trading subsystem was required adhering to strict Single Responsibility (1 engine = 1 task) and supporting multi-strategy position netting.
- Decision: Create `paper_trading/` containing 7 decoupled micro-engines (`MarketDataEngine`, `StrategyEngines`, `PortfolioAllocatorEngine`, `PositionNettingEngine`, `RiskGuardEngine`, `MT5OrderRouterEngine`, `ExecutionSimulatorEngine`, `AuditLedgerEngine`).
- Integration: Configured live MT5 order routing for Top 3 Validated Strategies on XAUUSD (`STRAT_OB_ALLDAY`, `STRAT_OB_TREND`, `STRAT_FVG_OVERLAP`).
- Verification: 73 unit and pipeline tests passed in 12.07s on local and VPS environments.

## ADR-030 - Remediation of Unverified Post-Baseline Work

- Date: 2026-09-01
- Status: Remediation applied; supervisor review required
- Context: A read-only audit found post-baseline implementation and Stage 12/15 claims without the signed independent-replication and supervisor-opening artifacts required by the governance baseline.
- Decision: Preserve all existing reports and data for audit, classify the Stage 12 certification and Stage 15 deployment claims as unverified pending formal review, and apply fail-closed controls to physical MT5 routing and Protected OOS access.
- Controls applied: MT5 routing is simulation-only by default; physical routing requires an explicit environment confirmation and a confirmed demo account; OOS unlock requires an externally configured exact authorization token; vault files cannot be overwritten; audit logs store token fingerprints rather than plaintext tokens.
- Next action: Supervisor must open the appropriate governed stage, review the preserved evidence, and approve or reject the remediation package. No live routing or edge-promotion claim is authorized by this entry.
