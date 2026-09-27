"""Unit and integration tests for empirical research capabilities, stylized facts, and hypothesis generation."""

import os
import tempfile
import pandas as pd
import pytest
from qros.research.capabilities import evaluate_data_sufficiency
from qros.research.hypothesis_generator import (
    generate_preregistered_hypotheses,
    persist_hypotheses_and_registry,
)
from qros.research.stylized_facts import StylizedFactsScanner
from qros.testing.synthetic_data import generate_synthetic_ohlcv
from qros.tracking.ledger import GlobalTrialLedger


def test_evaluate_data_sufficiency():
    # Construct dataframes with sufficient spans
    idx_m1 = pd.date_range(start="2026-01-01", periods=2000, freq="15min", tz="UTC")
    df_m1 = pd.DataFrame({"open": 100, "high": 101, "low": 99, "close": 100, "volume": 100}, index=idx_m1)

    idx_m5 = pd.date_range(start="2026-01-01", periods=1000, freq="2h", tz="UTC")
    df_m5 = pd.DataFrame({"open": 100, "high": 101, "low": 99, "close": 100, "volume": 100}, index=idx_m5)

    idx_h1 = pd.date_range(start="2024-01-01", periods=1000, freq="12h", tz="UTC")
    df_h1 = pd.DataFrame({"open": 100, "high": 101, "low": 99, "close": 100, "volume": 100}, index=idx_h1)

    idx_d1 = pd.date_range(start="2020-01-01", periods=500, freq="1D", tz="UTC")
    df_d1 = pd.DataFrame({"open": 100, "high": 101, "low": 99, "close": 100, "volume": 100}, index=idx_d1)

    data_map = {
        "M1": df_m1,
        "M5": df_m5,
        "H1": df_h1,
        "D1": df_d1,
    }

    results = evaluate_data_sufficiency(data_map)

    assert "CLASS-I" in results
    assert "CLASS-II" in results
    assert "CLASS-III" in results
    assert "CLASS-IV" in results
    assert "CLASS-V" in results

    # Class I, II, III should evaluate to True
    assert results["CLASS-I"].is_sufficient is True
    assert results["CLASS-II"].is_sufficient is True
    assert results["CLASS-III"].is_sufficient is True
    # Class IV requires 3000 daily observations over 12 years -> insufficient on 500 bars
    assert results["CLASS-IV"].is_sufficient is False
    assert results["CLASS-IV"].status_label == "DATA INSUFFICIENT"
    # Class V requires cross-asset data -> insufficient
    assert results["CLASS-V"].is_sufficient is False
    assert results["CLASS-V"].status_label == "DATA INSUFFICIENT"


def test_stylized_facts_scanner():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_file = os.path.join(tmp_dir, "test_ledger.json")
        ledger = GlobalTrialLedger(ledger_path=ledger_file)

        df_m1 = generate_synthetic_ohlcv(n_bars=600, freq="1min", random_seed=42)
        df_m5 = generate_synthetic_ohlcv(n_bars=600, freq="5min", random_seed=42)
        df_h1 = generate_synthetic_ohlcv(n_bars=400, freq="1h", random_seed=42)
        df_d1 = generate_synthetic_ohlcv(n_bars=200, freq="1D", random_seed=42)

        data_map = {
            "M1": df_m1,
            "M5": df_m5,
            "H1": df_h1,
            "D1": df_d1,
        }

        scanner = StylizedFactsScanner(data_map=data_map, ledger=ledger)
        observations = scanner.scan_all_domains()

        assert len(observations) == 18
        assert ledger.global_k >= 18

        # Check domain 1 observation structure
        obs_1 = observations[0]
        assert obs_1.observation_id == "QROS-OBS-001"
        assert obs_1.domain_id == 1
        assert obs_1.statistical_metric_name is not None
        assert obs_1.plausible_economic_rationale is not None


def test_preregistered_hypotheses_quality_gates():
    with tempfile.TemporaryDirectory() as tmp_dir:
        hypotheses = generate_preregistered_hypotheses()
        assert len(hypotheses) >= 3

        for hyp in hypotheses:
            gates = hyp.validate_quality_standard()
            assert all(gates.values()) is True, f"Hypothesis {hyp.hypothesis_id} failed quality gates: {gates}"
            assert hyp.hypothesis_id.startswith("QROS-HYP-")
            assert hyp.research_class in ["CLASS-I", "CLASS-II", "CLASS-III", "CLASS-IV", "CLASS-V"]
            assert hyp.validation_profile is not None

        reg_file = persist_hypotheses_and_registry(hypotheses, base_dir=tmp_dir)
        assert os.path.exists(reg_file)
        assert os.path.exists(os.path.join(tmp_dir, "hypotheses", "QROS-HYP-000001.yaml"))
