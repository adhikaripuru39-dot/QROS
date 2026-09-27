"""Empirical test runner for QROS-HYP-000001 on v4.0.0 non-OOS dataset."""

import os
import sys
import yaml
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))

from qros.research.tester import HypothesisTester
from qros.schemas.hypothesis import HypothesisRecord
from qros.schemas.validation_profile import ValidationProfile
from qros.tracking.ledger import GlobalTrialLedger
from qros.data.validation import compute_dataset_hash

# 1. Load pre-registered hypothesis
hyp_path = "docs/research/registry/hypotheses/QROS-HYP-000001.yaml"
with open(hyp_path, "r") as fp:
    hyp_dict = yaml.safe_load(fp)

val_prof = ValidationProfile(**hyp_dict.get("validation_profile", {}))
hyp_dict["validation_profile"] = val_prof
hypothesis = HypothesisRecord(**hyp_dict)

# 2. Load non-OOS M5 dataset (Tiers 1, 2, and 3)
t1 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier1_eda.parquet")
t2 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier2_train.parquet")
t3 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier3_val.parquet")
df_non_oos = pd.concat([t1, t2, t3]).sort_index()

print("=" * 80)
print("EMPIRICAL INTRADAY HYPOTHESIS TEST: QROS-HYP-000001 (London Open Breakout)")
print("=" * 80)
print(f"Asset: {hypothesis.asset} | Timeframe: {hypothesis.timeframe} | Class: {hypothesis.research_class}")
print(f"Non-OOS Bars Ingested: {len(df_non_oos):,d} (Span: {df_non_oos.index[0]} to {df_non_oos.index[-1]})")

# 3. Execute tester
ledger = GlobalTrialLedger()
tester = HypothesisTester(ledger=ledger)
dataset_hash = compute_dataset_hash(df_non_oos)

exp_record, stat_result, trades = tester.test_hypothesis_001(
    df_m5=df_non_oos,
    hypothesis=hypothesis,
    dataset_hash=dataset_hash,
    experiment_id="QROS-EXP-000010",
    dataset_version="v4.0.0",
)

print("\n" + "-" * 80)
print("EMPIRICAL TEST RESULTS & STATISTICAL PROFILE")
print("-" * 80)
print(f"Total Trade Events (N): {stat_result.sample_size_n}")
print(f"Effective Trade Count (N_eff): {stat_result.effective_sample_size_neff:.1f}")
print(f"Observation Length (T): {stat_result.observation_count_t:,d} bars ({stat_result.calendar_span_years:.2f} Years)")
print(f"Net Profit Factor (after 2.5x slippage): {stat_result.profit_factor_net:.4f}")
print(f"Net Annualized Sharpe: {stat_result.annualized_sharpe_net:.4f}")
print(f"Net Annualized Sortino: {stat_result.annualized_sortino_net:.4f}")
print(f"t-Statistic: {stat_result.t_statistic:.4f} (p-value: {stat_result.p_value:.4f})")

if stat_result.bootstrap_result:
    bs = stat_result.bootstrap_result
    print(f"Stationary Block Bootstrap 95% CI: [{bs.ci_lower_95:.4f}, {bs.ci_upper_95:.4f}] (Strictly Positive: {bs.ci_strictly_positive})")

if stat_result.dsr_result:
    dsr = stat_result.dsr_result
    print(f"Deflated Sharpe Ratio (DSR) (K={dsr.trial_count_k}): {dsr.dsr_score:.4f} (Significant: {dsr.is_statistically_significant})")

print("\n" + "-" * 80)
print("GOVERNANCE GATES & CLASSIFICATION")
print("-" * 80)
print(f"Passed Sample Power (N >= {val_prof.min_trades}): {stat_result.passed_sample_power}")
print(f"Passed Profit Factor (PF >= {val_prof.target_profit_factor}): {stat_result.passed_profit_factor}")
print(f"Passed Sharpe Ratio (SR >= {val_prof.target_sharpe}): {stat_result.passed_sharpe}")
print(f"Passed DSR Hurdle (DSR >= {val_prof.dsr_hurdle}): {stat_result.passed_dsr}")
print(f"Passed Bootstrap 95% CI (> 0.0): {stat_result.passed_bootstrap_ci}")
print(f"Overall Gate Pass: {stat_result.overall_gate_pass}")
print(f"Failure Reasons: {stat_result.failure_reasons}")
print(f"\nFinal Hypothesis Status: [{exp_record.classification}]")
print("=" * 80)