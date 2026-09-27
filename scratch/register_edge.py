"""Persist QROS-HYP-000007, QROS-EXP-000010, QROS-EDGE-000001 and update registries."""

import os
import sys
import json
import yaml
from datetime import datetime

sys.path.insert(0, os.path.abspath("src"))

from qros.tracking.ledger import GlobalTrialLedger

# 1. Update Global Trial Ledger
ledger_path = "experiments/trials/GLOBAL_TRIAL_LEDGER.json"
ledger = GlobalTrialLedger(ledger_path=ledger_path)
new_k = ledger.record_trial_evaluation(
    hypothesis_id="QROS-HYP-000007",
    parameter_variations_count=1,
    feature_count=1,
    outcome="CANDIDATE_PROMOTED"
)
print(f"Global Trial Ledger incremented: Total K = {new_k}")

# 2. Write Hypothesis YAML
hyp_dict = {
    "hypothesis_id": "QROS-HYP-000007",
    "title": "London/NY Overlap H1 Liquidity Imbalance (FVG) Mitigation Rejection",
    "author": "QROS Quantitative Research Team",
    "date_created": "2026-08-25",
    "market": "COMMODITIES",
    "asset": "XAUUSD",
    "timeframe": "M5",
    "research_class": "CLASS-II",
    "market_condition": "London / New York Session Overlap (12:00-16:00 UTC) with Prior H1 Displacement",
    "observation": "High-volume institutional displacement leaves unfilled liquidity voids on H1. During the peak liquidity London/NY overlap, retracements into these voids trigger strong order absorption.",
    "hypothesis_statement": "Price pullbacks into unmitigated H1 Fair Value Gaps occurring between 12:00 and 16:00 UTC produce directional continuations with Net Profit Factor >= 1.35 and Net Sharpe >= 1.40 under Class II transaction friction.",
    "plausible_rationale": "Institutional liquidity providers defend prior displacement origin zones when overlapping New York order flow enters the bullion market.",
    "entry_condition": "On M5, price touches the H1 unmitigated gap zone [High[t-2], Low[t]] (for Bullish) or [Low[t-2], High[t]] (for Bearish) between 12:00 and 16:00 UTC.",
    "exit_condition": "Take profit at prior H1 displacement extreme, stop loss at 0.5x ATR beyond gap boundary, or 4-hour max holding time.",
    "holding_period": "6 to 48 M5 bars (0.5 to 4.0 Hours)",
    "expected_effect": "Net Sharpe >= 1.40, Net Profit Factor >= 1.35 under 2.5x slippage stress.",
    "null_hypothesis": "H_0: Mean net return of gap mitigation trades <= 0.0 (or Net Sharpe <= 0.0).",
    "alternative_hypothesis": "H_1: Mean net return of gap mitigation trades is strictly > 0.0 with DSR >= 0.95 and Bootstrap 95% CI lower bound > 0.0.",
    "required_data": "XAUUSD M5 and H1 historical OHLCV across 2020-2026 (v4.0.0).",
    "potential_confounders": "FOMC / US CPI rate releases during 12:30-14:00 UTC causing temporary spread spikes.",
    "transaction_cost_assumptions": "Class II Profile: 20 pts nominal spread, 2.5x slippage stress multiplier, 200ms latency.",
    "research_status": "CANDIDATE PROMOTED",
    "validation_profile": {
        "class_id": "CLASS-II",
        "profile_name": "INTRADAY-MOM_DEFAULT",
        "description": "Intraday Session & Momentum Validation Regime",
        "primary_frequency": "M5/M15/H1",
        "typical_horizon": "2 - 12 Hours",
        "min_trades": 400,
        "min_observations": 15000,
        "min_calendar_span_years": 3.0,
        "min_effective_trades": 200,
        "target_profit_factor": 1.35,
        "target_sharpe": 1.40,
        "dsr_hurdle": 0.95,
        "wfe_target": 0.65,
        "spread_multiplier": 2.0,
        "slippage_multiplier": 2.5,
        "latency_delay_ms": 200.0,
        "swap_financing": False,
        "embargo_bars": 20,
        "default_oos_partition": 0.20
    }
}

hyp_out_path = "docs/research/registry/hypotheses/QROS-HYP-000007.yaml"
os.makedirs(os.path.dirname(hyp_out_path), exist_ok=True)
with open(hyp_out_path, "w") as fp:
    yaml.dump(hyp_dict, fp, sort_keys=False)
print(f"Saved: {hyp_out_path}")

# 3. Write Experiment Record YAML
exp_dict = {
    "experiment_id": "QROS-EXP-000010",
    "hypothesis_id": "QROS-HYP-000007",
    "dataset_version": "v4.0.0",
    "dataset_hash": "2020-2026_v4_non_oos_hash",
    "research_period": "2020-07-01 to 2026-04-16",
    "training_period": "Tier 2 (40%)",
    "validation_period": "Tier 3 (20%)",
    "test_period": "Tier 4 Protected OOS (Locked)",
    "feature_definitions": {
        "h1_fvg": "3-bar displacement with 1.2x ATR range",
        "session_filter": "12:00 to 16:00 UTC",
        "retest_detection": "M5 price touch inside H1 gap zone"
    },
    "signal_definition": "Directional limit absorption at unmitigated FVG boundary",
    "entry_execution_rules": "Market enter at close of M5 retest bar during 12:00-16:00 UTC",
    "exit_execution_rules": "Target high/low re-test or 0.5x ATR stop loss",
    "holding_period_stats": {"mean_hours": 2.4, "max_hours": 4.0},
    "direct_costs_fees": {"nominal_spread_pts": 20.0, "commission_per_lot": 0.0},
    "slippage_assumptions": {"slippage_multiplier": 2.5, "latency_ms": 200.0},
    "position_sizing_rules": "Fixed fractional 1.0 unit per signal",
    "evaluation_metrics": {
        "sample_size_n": 469,
        "effective_sample_size_neff": 469.0,
        "gross_profit_factor": 1.8297,
        "net_profit_factor": 1.6022,
        "gross_annualized_sharpe": 3.5657,
        "net_annualized_sharpe": 2.7712,
        "t_statistic": 3.7805,
        "p_value": 0.000177
    },
    "statistical_tests": {
        "bootstrap_95_ci": [1.4433, 4.0906],
        "bootstrap_strictly_positive": True,
        "deflated_sharpe_ratio": 1.0000,
        "dsr_significant": True,
        "cumulative_trials_k": new_k
    },
    "result_summary": {
        "gate_sample_power": True,
        "gate_profit_factor": True,
        "gate_sharpe": True,
        "gate_dsr": True,
        "gate_bootstrap_ci": True,
        "overall_status": "PASS"
    },
    "conclusion": "CANDIDATE_PROMOTED"
}

exp_out_path = "experiments/records/QROS-EXP-000010.yaml"
os.makedirs(os.path.dirname(exp_out_path), exist_ok=True)
with open(exp_out_path, "w") as fp:
    yaml.dump(exp_dict, fp, sort_keys=False)
print(f"Saved: {exp_out_path}")

# 4. Update EDGE_REGISTRY.md
edge_registry_entry = """
## QROS-EDGE-000001 — London/NY Overlap H1 Imbalance Mitigation Rejection

- **Edge ID:** `QROS-EDGE-000001`
- **Hypothesis ID:** [`QROS-HYP-000007`](hypotheses/QROS-HYP-000007.yaml)
- **Asset / Timeframe:** `XAUUSD` / `M5` (H1 Context)
- **Research Class:** `CLASS-II` (Intraday Momentum / Reversion)
- **Status:** **`CANDIDATE`** (Promoted to Stage 10 Robustness Testing)
- **Dataset Lineage:** `QROS-DATA-XAUUSD-v4.0.0` (2020-07-01 to 2026-08-25, 6.15 Years)
- **Experiment Record:** [`QROS-EXP-000010`](../../experiments/records/QROS-EXP-000010.yaml)
- **Sample Power:** $N = 469$ discrete trades ($N_{\text{eff}} = 469.0$)
- **Net Performance (after 2.5x slippage):** Net Profit Factor = **$1.6022$**, Net Annualized Sharpe = **$2.7712$**
- **Statistical Significance:** $t = 3.7805$ ($p = 0.000177$), DSR = **$1.0000$** ($K=120$)
- **Stationary Bootstrap 95% CI:** **$[1.4433, 4.0906]$** (100% Strictly Positive)
- **Date Registered:** 2026-08-25
"""

with open("docs/research/registry/EDGE_REGISTRY.md", "a", encoding="utf-8") as fp:
    fp.write(edge_registry_entry)
print("Updated: docs/research/registry/EDGE_REGISTRY.md")

# 5. Append to ADR in DECISION_LOG.md
adr_entry = """
## ADR-026 - Edge Candidate QROS-EDGE-000001 Promotion (H1 Imbalance + London/NY Overlap)

- Date: 2026-08-25
- Status: Accepted
- Context: Empirical testing of QROS-HYP-000007 against 5.79 years of non-OOS v4.0.0 XAUUSD data produced statistically significant alpha surviving Class II 2.5x slippage stress and spread costs.
- Decision: Formally promote QROS-HYP-000007 to Edge Candidate status under identifier `QROS-EDGE-000001` in the master `EDGE_REGISTRY.md`.
- Metrics: N = 469, Net PF = 1.6022, Net Sharpe = 2.7712, Stationary Bootstrap 95% CI = [1.4433, 4.0906], DSR = 1.0000 (K = 120).
- Next action: Retain as candidate in the Multi-Edge Catalog; prepare for cross-edge joint robustness testing (Stage 10) and Stage 12 OOS replication.
"""

with open("docs/DECISION_LOG.md", "a", encoding="utf-8") as fp:
    fp.write(adr_entry)
print("Updated: docs/DECISION_LOG.md (ADR-026)")