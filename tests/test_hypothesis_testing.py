"""Unit and integration tests for empirical hypothesis testing engine and experiment records."""

import os
import tempfile
import pandas as pd
import pytest
from qros.research.hypothesis_generator import generate_preregistered_hypotheses
from qros.research.tester import HypothesisTester, TradeEvent
from qros.schemas.experiment import ExperimentRecord
from qros.testing.synthetic_data import generate_synthetic_ohlcv
from qros.tracking.ledger import GlobalTrialLedger


def test_hypothesis_tester_execution():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_ledger.json")
        ledger = GlobalTrialLedger(ledger_path=ledger_path)
        tester = HypothesisTester(ledger=ledger, random_seed=42)

        hypotheses = generate_preregistered_hypotheses()
        hyp1 = [h for h in hypotheses if h.hypothesis_id == "QROS-HYP-000001"][0]
        hyp2 = [h for h in hypotheses if h.hypothesis_id == "QROS-HYP-000002"][0]
        hyp3 = [h for h in hypotheses if h.hypothesis_id == "QROS-HYP-000003"][0]

        df_m5 = generate_synthetic_ohlcv(n_bars=1000, freq="5min", random_seed=42)
        df_h1 = generate_synthetic_ohlcv(n_bars=800, freq="1h", random_seed=42)
        df_d1 = generate_synthetic_ohlcv(n_bars=400, freq="1D", random_seed=42)

        # Test 1: M5 London Open Breakout
        exp1, stat1, trades1 = tester.test_hypothesis_001(
            df_m5, hyp1, "HASH-M5", experiment_id="QROS-EXP-000004", dataset_version="v3.0.0"
        )
        assert isinstance(exp1, ExperimentRecord)
        assert exp1.experiment_id == "QROS-EXP-000004"
        assert exp1.dataset_version == "v3.0.0"
        assert exp1.conclusion in ["REJECTED", "PROMISING", "INCONCLUSIVE", "DATA INSUFFICIENT"]
        assert len(exp1.evaluation_metrics) > 0

        # Test 2: H1 Volatility Compression
        exp2, stat2, trades2 = tester.test_hypothesis_002(
            df_h1, hyp2, "HASH-H1", experiment_id="QROS-EXP-000005", dataset_version="v3.0.0"
        )
        assert isinstance(exp2, ExperimentRecord)
        assert exp2.experiment_id == "QROS-EXP-000005"
        assert exp2.conclusion in ["REJECTED", "PROMISING", "INCONCLUSIVE", "DATA INSUFFICIENT"]

        # Test 3: D1 Mean Reversion
        exp3, stat3, trades3 = tester.test_hypothesis_003(
            df_d1, hyp3, "HASH-D1", experiment_id="QROS-EXP-000006", dataset_version="v3.0.0"
        )
        assert isinstance(exp3, ExperimentRecord)
        assert exp3.experiment_id == "QROS-EXP-000006"
        assert exp3.conclusion in ["REJECTED", "PROMISING", "INCONCLUSIVE", "DATA INSUFFICIENT"]

        # Test 4: D1 50-Day High Momentum (HYP-004)
        from qros.research.hypothesis_generator import generate_expanded_hypotheses_r008
        hyps_r008 = generate_expanded_hypotheses_r008()
        hyp4 = [h for h in hyps_r008 if h.hypothesis_id == "QROS-HYP-000004"][0]
        exp4, stat4, trades4 = tester.test_hypothesis_004(
            hyp4, df_d1, "HASH-D1", experiment_id="QROS-EXP-000007", dataset_version="v3.0.0"
        )
        assert isinstance(exp4, ExperimentRecord)
        assert exp4.experiment_id == "QROS-EXP-000007"
        assert exp4.conclusion in ["REJECTED", "EDGE CANDIDATE ELIGIBLE", "INCONCLUSIVE", "DATA INSUFFICIENT"]

        # Test 5: D1 NR4 Range Compression (HYP-005)
        hyp5 = [h for h in hyps_r008 if h.hypothesis_id == "QROS-HYP-000005"][0]
        exp5, stat5, trades5 = tester.test_hypothesis_005(
            hyp5, df_d1, "HASH-D1", experiment_id="QROS-EXP-000008", dataset_version="v3.0.0"
        )
        assert isinstance(exp5, ExperimentRecord)
        assert exp5.experiment_id == "QROS-EXP-000008"

        # Test 6: Cross-Timeframe Breakout (HYP-006)
        hyp6 = [h for h in hyps_r008 if h.hypothesis_id == "QROS-HYP-000006"][0]
        exp6, stat6, trades6 = tester.test_hypothesis_006(
            hyp6, df_h1, df_d1, "HASH-H1", experiment_id="QROS-EXP-000009", dataset_version="v3.0.0"
        )
        assert isinstance(exp6, ExperimentRecord)
        assert exp6.experiment_id == "QROS-EXP-000009"

        # Check ExperimentRecord YAML serialization
        yaml_str = exp1.to_yaml()
        loaded_exp = ExperimentRecord.from_yaml(yaml_str)
        assert loaded_exp.experiment_id == exp1.experiment_id
        assert loaded_exp.hypothesis_id == exp1.hypothesis_id


def test_trade_event_dataclass():
    now = pd.Timestamp.now(tz="UTC")
    trade = TradeEvent(
        entry_time=now,
        exit_time=now + pd.Timedelta(hours=2),
        direction=1,
        entry_price=2500.0,
        exit_price=2510.0,
        holding_bars=24,
        gross_return=0.004,
        net_return=0.003,
        friction_deduction=0.001,
    )
    assert trade.direction == 1
    assert trade.net_return < trade.gross_return
