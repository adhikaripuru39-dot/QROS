"""QROS Data package: integrity validation, 4-tier splitting, quality audit, and vaulted storage."""

from qros.data.validation import (
    validate_ohlcv_dataframe,
    compute_dataset_hash,
    DataValidationReport,
)
from qros.data.splitting import (
    DataSplitter,
    SplitDataset,
    ProtectedOOSViolationError,
    PartitionMetadata,
)
from qros.data.purging import (
    purge_overlapping_labels,
    compute_embargo_cutoff,
    purged_train_test_split,
)
from qros.data.quality import (
    audit_dataset_quality,
    ComprehensiveDataQualityReport,
    QualityCheckResult,
)
from qros.data.adapters import (
    BaseIngestionAdapter,
    MT5IngestionAdapter,
    CSVIngestionAdapter,
)
from qros.data.vault import (
    DatasetManifest,
    DatasetRegistry,
    PartitionInfo,
    ProtectedOOSVault,
)

__all__ = [
    "validate_ohlcv_dataframe",
    "compute_dataset_hash",
    "DataValidationReport",
    "DataSplitter",
    "SplitDataset",
    "ProtectedOOSViolationError",
    "PartitionMetadata",
    "purge_overlapping_labels",
    "compute_embargo_cutoff",
    "purged_train_test_split",
    "audit_dataset_quality",
    "ComprehensiveDataQualityReport",
    "QualityCheckResult",
    "BaseIngestionAdapter",
    "MT5IngestionAdapter",
    "CSVIngestionAdapter",
    "DatasetManifest",
    "DatasetRegistry",
    "PartitionInfo",
    "ProtectedOOSVault",
]
