"""AuditLedgerEngine: Single Responsibility = Persist Immutable Event Audit Trail."""

import json
import os
from dataclasses import asdict
from typing import Any


class AuditLedgerEngine:
    """Appends all paper trading events into a JSONL audit ledger."""

    def __init__(self, log_path: str = "paper_trading/logs/PAPER_AUDIT_LEDGER.jsonl") -> None:
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def record_event(self, event_type: str, event_obj: Any) -> None:
        payload = {
            "event_type": event_type,
            "data": asdict(event_obj) if hasattr(event_obj, "__dataclass_fields__") else str(event_obj),
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
