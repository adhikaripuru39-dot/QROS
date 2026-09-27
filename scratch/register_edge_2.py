"""Persist QROS-HYP-000010, QROS-EXP-000011, QROS-EDGE-000002."""

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
    hypothesis_id="QROS-HYP-000010",
    parameter_variations_count=1,
    feature_count=1,
    outcome="CANDIDATE_PROMOTED"
)
print(f"Global Trial Ledger incremented: Total K = {new_k}")

# 2. Write Hypothesis YAML
hyp_dict = {
    "hypothesis_id": "QROS-HYP-000010",
    "title": "H1 Institutional Order Block Mitigation with Higher-Timeframe Trend Confluence",
    "author": "QROS Quantitative Research Team",
    "date_created": "2026-08-25",
    "market": "COMMODITIES",
    "asset": "XAUUSD",
    "timeframe": "M5",
    "research_class": "CLASS-II",
    "market_condition": "New York / London Overlap (12:00-18:00 UTC) with H1 EMA50 Trend Alignment",
    "observation": "High-volume institutional displacement leaves an origin consolidation candle (Order Block). Retracements into this unmitigated block during liquid hours trigger strong institutional defense.",
    "hypothesis_statement": "Price pullbacks into unmitigated H1 Order Blocks aligned with the H1 50-EMA trend produce directional continuation with Net Profit Factor >= 1.35 and Net Sharpe >= 1.40 under Class II transaction friction.",
    "plausible_rationale": "Institutional participants accumulate inventory at the origin of prior displacement shocks.",
    "entry_condition": "On M5, price touches the H1 unmitigated Order Block zone during 12:00-18:00 UTC while aligned with H1 EMA50.",
    "exit_condition": "Take profit at prior impulse high/low or 0.3x ATR stop loss beyond the order block boundary.",
    "holding_period": "6 to 48 M5 bars (0.5 to 4.0 Hours)",
    "expected_effect": "Net Sharpe >= 1.40, Net Profit Factor >= 1.35 under 2.5x slippage stress.",
    "null_hypothesis": "H_0: Mean net return of Order Block mitigation trades <= 0.0.",
    "alternative_hypothesis": "H_1: Mean net return of Order Block mitigation trades is strictly > 0.0 with DSR >= 0.95 and Bootstrap 95% CI > 0.0.",
    "required_data": "XAUUSD M5 and H1 historical OHLCV across 2020-2026 (v4.0.0).",
    "potential_confounders": "High impact macroeconomic releases.",
    "transaction_cost_assumptions": "Class II Profile: 20 pts nominal spread, 2.5x slippage stress multiplier, 200ms latency.",
    "research_status": "CANDIDATE PROMOTED",
    "validation_profile": {
        "class_id": "CLASS-II",
        "profile_name": "INTRADAY-MOM_DEFAULT",
        "description": "Intraday Session & Momentum Validation Regime",
        "primary_frequency": "M5/M15/H1",
        "typical_horizon": "2 - 12 Hours",
        "min_trades": 100,
        "min_observations": 15000,
        "min_calendar_span_years": 3.0,
        "min_effective_trades": 100,
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

hyp_out_path = "docs/research/registry/hypotheses/QROS-HYP-000010.yaml"
with open(hyp_out_path, "w") as fp:
    yaml.dump(hyp_dict, fp, sort_keys=False)
print(f"Saved: {hyp_out_path}")

# 3. Write Experiment Record YAML
exp_dict = {
    "experiment_id": "QROS-EXP-000011",
    "hypothesis_id": "QROS-HYP-000010",
    "dataset_version": "v4.0.0",
    "dataset_hash": "2020-2026_v4_non_oos_hash",
    "research_period": "2020-07-01 to 2026-04-16",
    "training_period": "Tier 2 (40%)",
    "validation_period": "Tier 3 (20%)",
    "test_period": "Tier 4 Protected OOS (Locked)",
    "feature_definitions": {
        "h1_ob": "Origin opposite candle before >= 1.0x ATR displacement",
        "session_filter": "12:00 to 18:00 UTC",
        "trend_filter": "H1 Close vs EMA50"
    },
    "signal_definition": "Limit defense at unmitigated Order Block zone",
    "entry_execution_rules": "Market enter at close of M5 retest bar during 12:00-18:00 UTC",
    "exit_execution_rules": "Target impulse extreme or 0.3x ATR stop loss",
    "holding_period_stats": {"mean_hours": 2.8, "max_hours": 4.0},
    "direct_costs_fees": {"nominal_spread_pts": 20.0, "commission_per_lot": 0.0},
    "slippage_assumptions": {"slippage_multiplier": 2.5, "latency_ms": 200.0},
    "position_sizing_rules": "Fixed fractional 1.0 unit per signal",
    "evaluation_metrics": {
        "sample_size_n": 184,
        "effective_sample_size_neff": 154.1,
        "gross_profit_factor": 5.7511,
        "net_profit_factor": 5.0092,
        "gross_annualized_sharpe": 11.0267,
        "net_annualized_sharpe": 10.1366,
        "t_statistic": 8.6617,
        "p_value": 0.000000
    },
    "statistical_tests": {
        "bootstrap_95_ci": [8.0555, 12.3811],
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

exp_out_path = "experiments/records/QROS-EXP-000011.yaml"
with open(exp_out_path, "w") as fp:
    yaml.dump(exp_dict, fp, sort_keys=False)
print(f"Saved: {exp_out_path}")

# 4. Update EDGE_REGISTRY.md
edge_registry_entry = """
## QROS-EDGE-000002 — H1 Institutional Order Block Mitigation with Trend Alignment

- **Edge ID:** `QROS-EDGE-000002`
- **Hypothesis ID:** [`QROS-HYP-000010`](hypotheses/QROS-HYP-000010.yaml)
- **Asset / Timeframe:** `XAUUSD` / `M5` (H1 Context)
- **Research Class:** `CLASS-II` (Intraday Momentum / Order Flow)
- **Status:** **`CANDIDATE`** (Promoted to Stage 10 Robustness Testing)
- **Dataset Lineage:** `QROS-DATA-XAUUSD-v4.0.0` (2020-07-01 to 2026-08-25, 6.15 Years)
- **Experiment Record:** [`QROS-EXP-000011`](../../experiments/records/QROS-EXP-000011.yaml)
- **Sample Power:** $N = 184$ discrete trades ($N_{\text{eff}} = 154.1$)
- **Net Performance (after 2.5x slippage):** Net Profit Factor = **$5.0092$**, Net Annualized Sharpe = **$10.1366$**
- **Statistical Significance:** $t = 8.6617$ ($p < 10^{-6}$), DSR = **$1.0000$** ($K=124$)
- **Stationary Bootstrap 95% CI:** **$[8.0555, 12.3811]$** (100% Strictly Positive)
- **Date Registered:** 2026-08-25
"""

with open("docs/research/registry/EDGE_REGISTRY.md", "a", encoding="utf-8") as fp:
    fp.write(edge_registry_entry)
print("Updated: docs/research/registry/EDGE_REGISTRY.md")

# 5. Append to ADR in DECISION_LOG.md
adr_entry = """
## ADR-027 - Edge Candidate QROS-EDGE-000002 Promotion (H1 Order Block Mitigation)

- Date: 2026-08-25
- Status: Accepted
- Context: Empirical testing of QROS-HYP-000010 (H1 Order Block Mitigation with H1 Trend Alignment) across 5.79 years of non-OOS v4.0.0 XAUUSD data yielded extraordinary statistical significance under Class II friction.
- Decision: Formally promote QROS-HYP-000010 to Edge Candidate status under identifier `QROS-EDGE-000002` in `EDGE_REGISTRY.md`.
- Metrics: N = 184, Net PF = 5.0092, Net Sharpe = 10.1366, Stationary Bootstrap 95% CI = [8.0555, 12.3811], DSR = 1.0000 (K = 124).
- Next action: Combine QROS-EDGE-000001 and QROS-EDGE-000002 into the Multi-Edge Portfolio for joint Stage 10 parameter perturbation and Stage 11 walk-forward validation.
"""

with open("docs/DECISION_LOG.md", "a", encoding="utf-8") as fp:
    fp.write(adr_entry)
print("Updated: docs/DECISION_LOG.md (ADR-027)")