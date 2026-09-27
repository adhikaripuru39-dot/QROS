"""QROS Testing & Synthetic Data package for controlled research verification."""

from qros.testing.synthetic_data import (
    generate_synthetic_ohlcv,
    generate_fat_tailed_returns,
    generate_autocorrelated_series,
    generate_corrupted_dataset,
)

__all__ = [
    "generate_synthetic_ohlcv",
    "generate_fat_tailed_returns",
    "generate_autocorrelated_series",
    "generate_corrupted_dataset",
]
