"""Protected Out-of-Sample Research Vault and governance locking."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hmac
import json
import os
from typing import Dict, Optional, Tuple
import pandas as pd
from qros.data.splitting import ProtectedOOSViolationError
from qros.data.validation import compute_dataset_hash


@dataclass
class VaultAuditEntry:
    """Audit trail record for vault access attempts."""

    timestamp_utc: str
    action: str
    dataset_id: str
    authorization_token: str
    is_granted: bool
    details: str = ""


class ProtectedOOSVault:
    """Secure, immutable storage container for Tier 4 Protected Out-of-Sample datasets."""

    def __init__(self, vault_directory: Optional[str] = None) -> None:
        if vault_directory is None:
            vault_directory = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "vault")
            )
        self.vault_directory = vault_directory
        os.makedirs(self.vault_directory, exist_ok=True)
        self.audit_log_path = os.path.join(self.vault_directory, "VAULT_AUDIT_LOG.json")
        self.audit_log = self._load_audit_log()

    def _load_audit_log(self) -> list:
        if os.path.exists(self.audit_log_path):
            try:
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _record_audit(
        self, action: str, dataset_id: str, token: str, is_granted: bool, details: str = ""
    ) -> None:
        entry = VaultAuditEntry(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            action=action,
            dataset_id=dataset_id,
            authorization_token=self._token_fingerprint(token),
            is_granted=is_granted,
            details=details,
        )
        self.audit_log.append(asdict(entry))
        with open(self.audit_log_path, "w", encoding="utf-8") as f:
            json.dump(self.audit_log, f, indent=2)

    @staticmethod
    def _token_fingerprint(token: str) -> str:
        """Keep secrets out of the audit log while retaining correlation evidence."""
        if not token:
            return ""
        import hashlib
        return "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()

    def vault_oos_dataset(
        self,
        df_oos: pd.DataFrame,
        dataset_id: str,
        symbol: str = "XAUUSD",
        timeframe: str = "M5",
    ) -> Tuple[str, str]:
        """Vault and persist Tier 4 Protected OOS dataset into immutable Parquet file.

        Returns
        -------
        Tuple[str, str]
            (Vault file path, SHA-256 hash).
        """
        filename = f"{dataset_id.lower()}_tier4_oos.parquet"
        file_path = os.path.join(self.vault_directory, filename)

        if os.path.exists(file_path):
            raise FileExistsError(
                f"Protected OOS dataset already exists and cannot be overwritten: {file_path}"
            )

        # Write Parquet with pyarrow
        df_oos.to_parquet(file_path, compression="snappy")
        file_hash = compute_dataset_hash(df_oos)

        self._record_audit(
            action="VAULT_STORAGE",
            dataset_id=dataset_id,
            token="SYSTEM_INIT",
            is_granted=True,
            details=f"Stored {len(df_oos)} bars in {file_path}. Hash={file_hash}",
        )

        return file_path, file_hash

    def load_vaulted_oos(
        self,
        dataset_id: str,
        authorization_token: str,
    ) -> pd.DataFrame:
        """Unlock and load the vaulted Tier 4 OOS dataset.

        Requires a token configured outside the repository via QROS_OOS_AUTH_TOKEN.
        """
        expected_token = os.getenv("QROS_OOS_AUTH_TOKEN", "")
        if (
            not authorization_token
            or not authorization_token.strip()
            or not expected_token
            or not hmac.compare_digest(authorization_token, expected_token)
        ):
            self._record_audit(
                action="UNAUTHORIZED_READ_ATTEMPT",
                dataset_id=dataset_id,
                token=authorization_token,
                is_granted=False,
                details="Rejected missing, unconfigured, or invalid authorization token.",
            )
            raise ProtectedOOSViolationError(
                "Access Denied: Non-empty governance authorization token is required to unlock Tier 4 OOS."
            )

        filename = f"{dataset_id.lower()}_tier4_oos.parquet"
        file_path = os.path.join(self.vault_directory, filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Vaulted OOS file not found: {file_path}")

        df = pd.read_parquet(file_path)

        self._record_audit(
            action="AUTHORIZED_OOS_UNLOCK",
            dataset_id=dataset_id,
            token=authorization_token,
            is_granted=True,
            details=f"Successfully unlocked {len(df)} bars for Gate 11 evaluation.",
        )

        return df
