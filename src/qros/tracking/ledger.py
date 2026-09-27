"""Global Experimentation Ledger and Trial Counter ($K$) management."""

from dataclasses import asdict, dataclass, field
import json
import os
import threading
from typing import Any, Dict, Optional


@dataclass
class LedgerState:
    """State of the QROS Global Experimentation Ledger."""

    total_hypotheses_generated: int = 0
    total_hypotheses_tested: int = 0
    total_feature_combinations_explored: int = 0
    total_parameter_variations_evaluated: int = 0  # Global K
    total_hypotheses_rejected: int = 0
    total_promising_hypotheses: int = 0
    total_edge_candidates_promoted: int = 0
    total_confirmed_edges_validated: int = 0
    last_updated_timestamp: str = ""
    trial_records: Dict[str, Any] = field(default_factory=dict)


class GlobalTrialLedger:
    """Thread-safe persistent ledger tracking all hypothesis and trial variations ($K$) in QROS."""

    def __init__(self, ledger_path: Optional[str] = None) -> None:
        if ledger_path is None:
            # Default location under docs/research/tracking/
            base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "research", "tracking")
            )
            os.makedirs(base_dir, exist_ok=True)
            ledger_path = os.path.join(base_dir, "TRIAL_LEDGER.json")

        self.ledger_path = ledger_path
        self._lock = threading.Lock()
        self.state = self._load()

    def _load(self) -> LedgerState:
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return LedgerState(**data)
            except Exception:
                return LedgerState()
        return LedgerState()

    def save(self) -> None:
        """Persist current ledger state to JSON file."""
        with self._lock:
            parent_dir = os.path.dirname(self.ledger_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.state), f, indent=2)

    def record_trial_evaluation(
        self,
        hypothesis_id: str,
        parameter_variations_count: int = 1,
        feature_count: int = 1,
        outcome: str = "TESTED",
    ) -> int:
        """Record an experiment trial evaluation and increment global $K$.

        Parameters
        ----------
        hypothesis_id : str
            Parent hypothesis identifier.
        parameter_variations_count : int
            Number of parameter combinations evaluated in this run.
        feature_count : int
            Number of feature combinations explored.
        outcome : str
            Outcome status (e.g., 'REJECTED', 'PROMISING', 'CANDIDATE_PROMOTED').

        Returns
        -------
        int
            Updated global cumulative trial count $K$.
        """
        with self._lock:
            self.state.total_hypotheses_tested += 1
            self.state.total_parameter_variations_evaluated += max(
                1, parameter_variations_count
            )
            self.state.total_feature_combinations_explored += max(
                1, feature_count
            )

            out = outcome.upper().strip()
            if out == "REJECTED":
                self.state.total_hypotheses_rejected += 1
            elif out == "PROMISING":
                self.state.total_promising_hypotheses += 1
            elif out == "CANDIDATE_PROMOTED":
                self.state.total_edge_candidates_promoted += 1
            elif out == "CONFIRMED":
                self.state.total_confirmed_edges_validated += 1

            self.state.trial_records[hypothesis_id] = {
                "parameter_variations": parameter_variations_count,
                "feature_count": feature_count,
                "outcome": out,
                "cumulative_k": self.state.total_parameter_variations_evaluated,
            }

        self.save()
        return self.state.total_parameter_variations_evaluated

    @property
    def global_k(self) -> int:
        """Get the current global total parameter variations count $K$."""
        return max(1, self.state.total_parameter_variations_evaluated)
