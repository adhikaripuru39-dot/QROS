"""Stationary Block Bootstrap resampling framework (Politis & Romano, 1994).

References
----------
Politis, D. N., & Romano, J. P. (1994). The Stationary Bootstrap.
Journal of the American Statistical Association, 89(428), 1303-1313.
"""

from typing import Callable, Optional, Tuple
import numpy as np
from qros.schemas.results import BootstrapResult


class StationaryBlockBootstrap:
    """Politis & Romano (1994) Stationary Bootstrap for stationary time-series dependency preservation.

    Uses random block lengths drawn from a Geometric distribution with parameter p = 1 / expected_block_length.
    Wraps indices circularly to guarantee stationarity.
    """

    def __init__(
        self,
        expected_block_length: float = 10.0,
        random_seed: Optional[int] = None,
    ) -> None:
        if expected_block_length <= 0:
            raise ValueError("expected_block_length must be strictly positive")
        self.expected_block_length = expected_block_length
        self.p = 1.0 / expected_block_length
        self.rng = np.random.default_rng(random_seed)

    def resample_indices(self, n_samples: int) -> np.ndarray:
        """Generate a single stationary bootstrap resampled index sequence of length n_samples."""
        indices = np.empty(n_samples, dtype=np.int64)

        current_idx = self.rng.integers(0, n_samples)
        for i in range(n_samples):
            # With probability p, start a new block at a random location
            if i > 0 and self.rng.random() < self.p:
                current_idx = self.rng.integers(0, n_samples)
            else:
                if i > 0:
                    current_idx = (current_idx + 1) % n_samples

            indices[i] = current_idx

        return indices

    def generate_resamples(
        self, data: np.ndarray, n_resamples: int = 5000
    ) -> np.ndarray:
        """Generate (n_resamples, n_samples) matrix of resampled data arrays."""
        arr = np.asarray(data)
        n = len(arr)
        resamples = np.empty((n_resamples, n), dtype=arr.dtype)

        for b in range(n_resamples):
            idx = self.resample_indices(n)
            resamples[b] = arr[idx]

        return resamples


def bootstrap_sharpe_ci(
    returns: np.ndarray,
    n_resamples: int = 5000,
    expected_block_length: float = 10.0,
    ci_level: float = 0.95,
    random_seed: Optional[int] = 42,
) -> BootstrapResult:
    """Compute non-parametric Stationary Bootstrap Confidence Intervals for the Sharpe Ratio.

    Parameters
    ----------
    returns : np.ndarray
        Observed return series.
    n_resamples : int
        Number of bootstrap replications (default: 5,000).
    expected_block_length : float
        Mean block length parameter (1/p).
    ci_level : float
        Confidence level (default: 0.95).
    random_seed : Optional[int]
        Deterministic random seed.

    Returns
    -------
    BootstrapResult
        Container with mean bootstrap Sharpe, 95% lower and upper bounds, and positivity check.
    """
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    n = len(arr)

    if n < 5:
        return BootstrapResult(
            mean_sharpe=0.0,
            ci_lower_95=0.0,
            ci_upper_95=0.0,
            n_resamples=n_resamples,
            stationary_p=1.0 / expected_block_length,
            ci_strictly_positive=False,
        )

    # Adjust block length if data is short
    block_len = min(expected_block_length, float(n) / 2.0)
    block_len = max(1.0, block_len)

    bootstrapper = StationaryBlockBootstrap(
        expected_block_length=block_len, random_seed=random_seed
    )

    resampled_matrix = bootstrapper.generate_resamples(arr, n_resamples=n_resamples)

    # Vectorized Sharpe computation across rows
    means = np.mean(resampled_matrix, axis=1)
    stds = np.std(resampled_matrix, axis=1, ddof=1)
    stds = np.where(stds == 0.0, 1e-8, stds)
    bootstrap_sharpes = (means / stds) * np.sqrt(252.0)

    # Compute percentiles
    alpha = (1.0 - ci_level) / 2.0
    lower_pct = alpha * 100.0
    upper_pct = (1.0 - alpha) * 100.0

    ci_lower = float(np.percentile(bootstrap_sharpes, lower_pct))
    ci_upper = float(np.percentile(bootstrap_sharpes, upper_pct))
    mean_boot_sharpe = float(np.mean(bootstrap_sharpes))

    return BootstrapResult(
        mean_sharpe=mean_boot_sharpe,
        ci_lower_95=ci_lower,
        ci_upper_95=ci_upper,
        n_resamples=n_resamples,
        stationary_p=1.0 / block_len,
        ci_strictly_positive=(ci_lower > 0.0),
    )
