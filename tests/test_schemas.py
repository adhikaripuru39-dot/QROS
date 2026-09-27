"""Unit tests for QROS Schemas (ValidationProfile, HypothesisRecord, ExperimentRecord, Results)."""

import pytest
from qros.schemas.validation_profile import ValidationProfile, get_default_profile
from qros.schemas.hypothesis import HypothesisRecord
from qros.schemas.experiment import ExperimentRecord
from qros.schemas.results import StatisticalResult, DSRResult, BootstrapResult


def test_validation_profile_defaults():
    for cid in ["CLASS-I", "CLASS-II", "CLASS-III", "CLASS-IV", "CLASS-V"]:
        profile = get_default_profile(cid)
        assert profile.class_id == cid
        assert profile.min_trades > 0
        assert profile.target_profit_factor > 1.0
        assert profile.target_sharpe > 0.0
        assert profile.dsr_hurdle >= 0.90


def test_validation_profile_serialization():
    profile = get_default_profile("CLASS-II")
    yaml_str = profile.to_yaml()
    assert "CLASS-II" in yaml_str
    reloaded = ValidationProfile.from_yaml(yaml_str)
    assert reloaded.class_id == profile.class_id
    assert reloaded.min_trades == profile.min_trades

    json_str = profile.to_json()
    assert "INTRADAY-MOM_DEFAULT" in json_str
    reloaded_json = ValidationProfile.from_json(json_str)
    assert reloaded_json.target_sharpe == profile.target_sharpe


def test_invalid_validation_profile():
    with pytest.raises(ValueError, match="Invalid class_id"):
        ValidationProfile(class_id="INVALID_CLASS", profile_name="TEST")

    with pytest.raises(ValueError, match="min_trades must be positive"):
        ValidationProfile(class_id="CLASS-I", profile_name="TEST", min_trades=-5)


def test_hypothesis_record_validation():
    # Valid hypothesis
    hyp = HypothesisRecord(
        hypothesis_id="QROS-HYP-000001",
        market="Commodities",
        asset="XAUUSD",
        timeframe="M5",
        research_class="CLASS-II",
        market_condition="London Open Volatility Expansion",
        observation="Strong momentum drift after initial London breakout.",
        hypothesis_statement="M5 momentum breakout during London open yields positive drift over 12 bars.",
        plausible_rationale="London fixing and institutional liquidity participation creates session trend continuation.",
        entry_condition="Close > RollingHigh(20)",
        exit_condition="TimeStop(12) or VolatilityStop(2.0*ATR)",
        holding_period="12 bars (1 hour)",
        expected_effect="Forward mean return > 0.20 sigma",
        null_hypothesis="H_0: Mean forward return <= 0.0",
        alternative_hypothesis="H_1: Mean forward return > 0.0",
        required_data="XAUUSD M5 Tick-aggregated OHLCV",
        potential_confounders="US/UK Bank Holidays, NFP releases",
        transaction_cost_assumptions="20 pts spread, 8 pts slippage",
    )
    assert hyp.hypothesis_id == "QROS-HYP-000001"
    assert hyp.validation_profile is not None
    assert hyp.validation_profile.class_id == "CLASS-II"

    # Quality check
    quality = hyp.validate_quality_standard()
    assert all(quality.values())

    # Serialization
    yaml_str = hyp.to_yaml()
    assert "QROS-HYP-000001" in yaml_str
    reloaded = HypothesisRecord.from_yaml(yaml_str)
    assert reloaded.asset == "XAUUSD"


def test_invalid_hypothesis_id():
    with pytest.raises(ValueError, match="Invalid hypothesis_id"):
        HypothesisRecord(
            hypothesis_id="INVALID-HYP-ID",
            market="FX",
            asset="EURUSD",
            timeframe="H1",
            research_class="CLASS-III",
            market_condition="Trend",
            observation="Obs",
            hypothesis_statement="Statement is long enough to satisfy basic string checks.",
            plausible_rationale="Rationale",
            entry_condition="Entry",
            exit_condition="Exit",
            holding_period="10",
            expected_effect="Effect",
            null_hypothesis="H_0: Null",
            alternative_hypothesis="H_1: Alt",
            required_data="Data",
            potential_confounders="Confounders",
            transaction_cost_assumptions="Costs",
        )


def test_experiment_record():
    exp = ExperimentRecord(
        experiment_id="QROS-EXP-000001",
        hypothesis_id="QROS-HYP-000001",
        dataset_version="v1.0.0",
        dataset_hash="abc123hash",
        research_period="2020-2024",
        training_period="2020-2022",
        validation_period="2022-2023",
        test_period="2023-2024",
        feature_definitions={"ret_20": "close/close.shift(20)-1"},
        signal_definition="ret_20 > 0.002",
        entry_execution_rules="Next bar open",
        exit_execution_rules="12 bars exit",
        holding_period_stats={"mean": 12.0},
        direct_costs_fees={"commission": 5.0},
        slippage_assumptions={"slippage_pts": 8.0},
        position_sizing_rules="Fixed 1.0 lot",
        evaluation_metrics={"sharpe": 1.55, "pf": 1.42},
        statistical_tests={"dsr": 0.96},
        result_summary={"is_pass": True},
        conclusion="PROMISING",
    )
    assert exp.experiment_id == "QROS-EXP-000001"
    yaml_str = exp.to_yaml()
    assert "QROS-EXP-000001" in yaml_str
    reloaded = ExperimentRecord.from_yaml(yaml_str)
    assert reloaded.conclusion == "PROMISING"
