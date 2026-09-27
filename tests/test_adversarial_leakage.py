"""Adversarial stress and anti-leakage test suite for QROS governance enforcement.

Intentionally injects look-ahead leakage, dataset corruptions, unauthorized OOS access,
and concurrent trial ledger mutations to verify strict failure detection.
"""

import threading
import numpy as np
import pandas as pd
import pytest
from qros.data.purging import (
    compute_embargo_cutoff,
    purge_overlapping_labels,
    purged_train_test_split,
)
from qros.data.splitting import DataSplitter, ProtectedOOSViolationError
from qros.data.validation import validate_ohlcv_dataframe
from qros.schemas.hypothesis import HypothesisRecord
from qros.schemas.validation_profile import ValidationProfile
from qros.testing.synthetic_data import (
    generate_corrupted_dataset,
    generate_synthetic_ohlcv,
)
from qros.tracking.ledger import GlobalTrialLedger


def test_adversarial_oos_tampering_blocked():
    """Adversarially attempt to access Tier 4 OOS partition without authorization."""
    df = generate_synthetic_ohlcv(n_bars=200, random_seed=42)
    splitter = DataSplitter()
    split_ds = splitter.split(df, lock_oos=True)

    # 1. Direct property access must fail with ProtectedOOSViolationError
    with pytest.raises(ProtectedOOSViolationError, match="Access Denied: Tier 4 Out-of-Sample"):
        _ = split_ds.oos

    # 2. Attempting to unlock with blank / empty token must fail
    with pytest.raises(ValueError, match="non-empty governance authorization token"):
        split_ds.unlock_oos("")

    with pytest.raises(ValueError, match="non-empty governance authorization token"):
        split_ds.unlock_oos("   ")

    # 3. Legitimate authorized unlock succeeds
    split_ds.unlock_oos("GOVERNANCE-GATE-11-AUTH-TOKEN-2026")
    assert split_ds.is_oos_locked is False
    assert len(split_ds.oos) == 40  # 20% of 200


def test_adversarial_lookahead_overlap_purged():
    """Verify that multi-bar trades crossing train/test boundary are 100% purged."""
    # Create 10 trade events
    # Test period is from bar 50 to bar 70
    start_times = pd.date_range("2023-01-01 00:00", periods=10, freq="10h", tz="UTC")
    # Some events span 25 hours (cross boundary)
    end_times = start_times + pd.Timedelta(hours=25)

    test_start = start_times[4]  # bar 4
    test_end = start_times[6]  # bar 6

    keep_mask = purge_overlapping_labels(start_times, end_times, test_start, test_end)
    keep_mask_arr = np.asarray(keep_mask)

    # Any event starting before test_start but ending after test_start MUST be purged (False)
    for i in range(len(start_times)):
        st = start_times[i]
        et = end_times[i]
        overlaps = not ((et < test_start) or (st > test_end))
        if overlaps:
            assert keep_mask_arr[i] == False, f"Event {i} overlapped test window but was NOT purged!"
        else:
            assert keep_mask_arr[i] == True


def test_adversarial_dataset_corruptions_detected():
    """Verify that every type of dataset corruption is trapped by validation pipeline."""
    corruption_types = [
        "high_low_violation",
        "negative_price",
        "nan_values",
        "infinite_values",
        "non_monotonic_time",
        "duplicate_timestamps",
    ]

    for ctype in corruption_types:
        corrupted_df = generate_corrupted_dataset(corruption_type=ctype, n_bars=100)
        _, report = validate_ohlcv_dataframe(corrupted_df)

        assert report.is_valid is False, f"Corruption type '{ctype}' was NOT caught by validator!"
        assert len(report.detected_issues) > 0


def test_adversarial_schema_malformed_inputs():
    """Verify strict rejection of malformed hypothesis inputs and invalid classes."""
    # 1. Invalid regex hypothesis ID
    with pytest.raises(ValueError, match="Invalid hypothesis_id"):
        HypothesisRecord(
            hypothesis_id="INVALID_ID_999",
            market="FX",
            asset="EURUSD",
            timeframe="H1",
            research_class="CLASS-I",
            market_condition="Trend",
            observation="Obs",
            hypothesis_statement="Statement must be at least 20 chars long.",
            plausible_rationale="Rationale",
            entry_condition="Entry",
            exit_condition="Exit",
            holding_period="10",
            expected_effect="Effect",
            null_hypothesis="H_0: Null",
            alternative_hypothesis="H_1: Alt",
            required_data="Data",
            potential_confounders="None",
            transaction_cost_assumptions="None",
        )

    # 2. Empty mandatory fields
    with pytest.raises(ValueError, match="Hypothesis field 'plausible_rationale' cannot be empty"):
        HypothesisRecord(
            hypothesis_id="QROS-HYP-000099",
            market="FX",
            asset="EURUSD",
            timeframe="H1",
            research_class="CLASS-I",
            market_condition="Trend",
            observation="Obs",
            hypothesis_statement="Statement must be at least 20 chars long.",
            plausible_rationale="",  # Empty
            entry_condition="Entry",
            exit_condition="Exit",
            holding_period="10",
            expected_effect="Effect",
            null_hypothesis="H_0: Null",
            alternative_hypothesis="H_1: Alt",
            required_data="Data",
            potential_confounders="None",
            transaction_cost_assumptions="None",
        )


def test_adversarial_concurrent_trial_ledger():
    """Verify thread-safety and zero lost updates under concurrent trial increments."""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_path = os.path.join(tmp_dir, "concurrent_ledger.json")
        ledger = GlobalTrialLedger(ledger_path=ledger_path)

        n_threads = 10
        increments_per_thread = 20
        variations_per_increment = 5

        def worker(thread_id: int):
            for i in range(increments_per_thread):
                ledger.record_trial_evaluation(
                    hypothesis_id=f"QROS-HYP-T{thread_id:02d}-{i:03d}",
                    parameter_variations_count=variations_per_increment,
                    feature_count=2,
                    outcome="TESTED",
                )

        threads = [
            threading.Thread(target=worker, args=(t,)) for t in range(n_threads)
        ]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        expected_total_k = n_threads * increments_per_thread * variations_per_increment
        expected_hypotheses = n_threads * increments_per_thread

        assert ledger.global_k == expected_total_k
        assert ledger.state.total_hypotheses_tested == expected_hypotheses

        # Verify on-disk persistence matches memory
        reloaded = GlobalTrialLedger(ledger_path=ledger_path)
        assert reloaded.global_k == expected_total_k
        assert reloaded.state.total_hypotheses_tested == expected_hypotheses
