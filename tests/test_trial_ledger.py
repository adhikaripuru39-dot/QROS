"""Unit tests for Global Trial Ledger and trial counting ($K$)."""

import os
import tempfile
import pytest
from qros.tracking.ledger import GlobalTrialLedger


def test_trial_ledger_increment_and_persistence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger_file = os.path.join(tmp_dir, "test_ledger.json")
        ledger = GlobalTrialLedger(ledger_path=ledger_file)

        assert ledger.global_k == 1

        # Record a trial with 50 parameter variations
        k1 = ledger.record_trial_evaluation(
            hypothesis_id="QROS-HYP-000001",
            parameter_variations_count=50,
            feature_count=5,
            outcome="REJECTED",
        )
        assert k1 == 50
        assert ledger.state.total_hypotheses_tested == 1
        assert ledger.state.total_hypotheses_rejected == 1

        # Record another trial with 100 variations
        k2 = ledger.record_trial_evaluation(
            hypothesis_id="QROS-HYP-000002",
            parameter_variations_count=100,
            feature_count=10,
            outcome="PROMISING",
        )
        assert k2 == 150
        assert ledger.state.total_hypotheses_tested == 2
        assert ledger.state.total_promising_hypotheses == 1

        # Reload from disk into new instance
        reloaded_ledger = GlobalTrialLedger(ledger_path=ledger_file)
        assert reloaded_ledger.global_k == 150
        assert reloaded_ledger.state.total_hypotheses_tested == 2
