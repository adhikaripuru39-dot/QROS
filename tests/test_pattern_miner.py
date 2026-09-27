"""Unit tests for ConditionalPatternMiner and QROS-RESEARCH-008 pattern discovery."""

import os
import tempfile
import pandas as pd
import pytest
from qros.research.hypothesis_generator import generate_expanded_hypotheses_r008
from qros.research.pattern_miner import ConditionalPattern, ConditionalPatternMiner
from qros.testing.synthetic_data import generate_synthetic_ohlcv
from qros.tracking.ledger import GlobalTrialLedger


def test_conditional_pattern_miner_execution():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "test_ledger.json")
        ledger = GlobalTrialLedger(ledger_path=ledger_path)

        df_d1 = generate_synthetic_ohlcv(n_bars=600, freq="1D", random_seed=42)
        df_h1 = generate_synthetic_ohlcv(n_bars=1000, freq="1h", random_seed=42)

        data_map = {"D1": df_d1, "H1": df_h1}
        miner = ConditionalPatternMiner(data_map=data_map, ledger=ledger)

        patterns = miner.mine_all_patterns()

        assert len(patterns) == 6
        for pat in patterns:
            assert isinstance(pat, ConditionalPattern)
            assert pat.pattern_id.startswith("QROS-PAT-")
            assert pat.sample_size_total > 0
            assert isinstance(pat.p_value, float)
            assert isinstance(pat.is_hypothesis_candidate, bool)
            assert len(pat.economic_mechanism) > 0


def test_expanded_hypotheses_r008_quality_gates():
    hypotheses = generate_expanded_hypotheses_r008()
    assert len(hypotheses) == 3

    for hyp in hypotheses:
        gates = hyp.validate_quality_standard()
        assert all(gates.values()), f"Quality gate failed for {hyp.hypothesis_id}: {gates}"
        assert hyp.research_status == "PRE_REGISTERED"
        assert hyp.validation_profile is not None
