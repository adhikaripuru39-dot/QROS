"""Update GlobalTrialLedger with 105 trials from the Discovery Battery."""

import os
import sys

sys.path.insert(0, os.path.abspath("src"))

from qros.tracking.ledger import GlobalTrialLedger

ledger_path = "experiments/trials/GLOBAL_TRIAL_LEDGER.json"
ledger = GlobalTrialLedger(ledger_path=ledger_path)
new_k = ledger.record_trial_evaluation(
    hypothesis_id="QROS-BATTERY-INTRADAY-105",
    parameter_variations_count=105,
    feature_count=6,
    outcome="CANDIDATE_PROMOTED"
)
print(f"Global Trial Ledger updated: Total Cumulative K = {new_k}")