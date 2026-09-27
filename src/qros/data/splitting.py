"""4-Tier Chronological Data Partitioning and Protected Out-of-Sample Vault."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import pandas as pd


class ProtectedOOSViolationError(PermissionError):
    """Raised when an unauthorized access attempt is made on the protected Tier 4 Out-of-Sample partition."""

    pass


@dataclass
class PartitionMetadata:
    """Metadata and hashes for a single chronological data partition."""

    name: str
    bar_count: int
    start_time: str
    end_time: str
    percentage: float


@dataclass
class SplitDataset:
    """Container for the 4-tier chronological partitions with governance access controls."""

    eda: pd.DataFrame
    train: pd.DataFrame
    validation: pd.DataFrame
    _oos: pd.DataFrame
    is_oos_locked: bool = True
    metadata: Dict[str, PartitionMetadata] = field(default_factory=dict)

    @property
    def oos(self) -> pd.DataFrame:
        """Access the protected Tier 4 OOS partition.

        Raises ProtectedOOSViolationError if the partition is locked under governance.
        """
        if self.is_oos_locked:
            raise ProtectedOOSViolationError(
                "Access Denied: Tier 4 Out-of-Sample partition is locked under QROS Governance. "
                "Final OOS data may only be accessed once at Stage 11 review via unlock_oos()."
            )
        return self._oos

    def unlock_oos(self, authorization_token: str) -> None:
        """Formally unlock the protected OOS partition for single-evaluation Gate 11 testing."""
        if not authorization_token or not authorization_token.strip():
            raise ValueError(
                "A non-empty governance authorization token is required to unlock Tier 4 OOS."
            )
        self.is_oos_locked = False


class DataSplitter:
    """Enforces chronological 4-tier partitioning in compliance with QROS-STD-EXP-004."""

    def __init__(
        self,
        eda_pct: float = 0.20,
        train_pct: float = 0.40,
        val_pct: float = 0.20,
        oos_pct: float = 0.20,
    ) -> None:
        total = round(eda_pct + train_pct + val_pct + oos_pct, 6)
        if total != 1.0:
            raise ValueError(
                f"Split percentages must sum to 1.0. Received {eda_pct} + {train_pct} + {val_pct} + {oos_pct} = {total}"
            )
        self.eda_pct = eda_pct
        self.train_pct = train_pct
        self.val_pct = val_pct
        self.oos_pct = oos_pct

    def split(
        self, df: pd.DataFrame, lock_oos: bool = True
    ) -> SplitDataset:
        """Partition the dataset chronologically into Tier 1 (EDA), Tier 2 (Train), Tier 3 (Val), and Tier 4 (OOS).

        Parameters
        ----------
        df : pd.DataFrame
            Monotonically increasing chronological DataFrame.
        lock_oos : bool
            Whether to enforce governance lock on Tier 4 OOS partition.

        Returns
        -------
        SplitDataset
            The 4-tier partition container with governance protection.
        """
        n = len(df)
        if n < 20:
            raise ValueError(
                f"Dataset too small to partition into 4 tiers (N = {n}). Minimum 20 bars required."
            )

        idx_eda = int(n * self.eda_pct)
        idx_train = idx_eda + int(n * self.train_pct)
        idx_val = idx_train + int(n * self.val_pct)

        df_eda = df.iloc[:idx_eda].copy()
        df_train = df.iloc[idx_eda:idx_train].copy()
        df_val = df.iloc[idx_train:idx_val].copy()
        df_oos = df.iloc[idx_val:].copy()

        def make_meta(name: str, sub_df: pd.DataFrame, pct: float) -> PartitionMetadata:
            start = sub_df.index[0].isoformat() if len(sub_df) > 0 and hasattr(sub_df.index[0], "isoformat") else str(sub_df.index[0])
            end = sub_df.index[-1].isoformat() if len(sub_df) > 0 and hasattr(sub_df.index[-1], "isoformat") else str(sub_df.index[-1])
            return PartitionMetadata(
                name=name,
                bar_count=len(sub_df),
                start_time=start,
                end_time=end,
                percentage=pct,
            )

        metadata = {
            "tier_1_eda": make_meta("Tier 1: EDA", df_eda, self.eda_pct),
            "tier_2_train": make_meta("Tier 2: Train (IS)", df_train, self.train_pct),
            "tier_3_val": make_meta("Tier 3: Validation", df_val, self.val_pct),
            "tier_4_oos": make_meta("Tier 4: Protected OOS", df_oos, self.oos_pct),
        }

        return SplitDataset(
            eda=df_eda,
            train=df_train,
            validation=df_val,
            _oos=df_oos,
            is_oos_locked=lock_oos,
            metadata=metadata,
        )
