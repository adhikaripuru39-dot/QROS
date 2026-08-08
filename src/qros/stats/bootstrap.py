"""Part 8 ch.2: Resampling & non-parametric robustness — stationary bootstrap, permutation."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

def seed_all(seed: int) -> None:
    """Seed both Python's random and numpy for reproducibility."""
    import random

    random.seed(seed)
    np.random.seed(seed)


def stationary_bootstrap(
    x: np.ndarray,
    size: int,
    mean_block: float,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Politis & Romano stationary bootstrap.

    Block lengths are geometric with mean ``mean_block``; consecutive blocks are
    chained (wrapped around the sample) preserving local autocorrelation.
    """
    rng = rng or np.random.default_rng()
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return np.array([])
    out = np.empty(size, dtype=float)
    pos = 0
    while pos < size:
        start = rng.integers(0, n)
        block_len = 1 + int(rng.geometric(1.0 / mean_block))
        for _ in range(block_len):
            if pos >= size:
                break
            out[pos] = x[start]
            pos += 1
            start = (start + 1) % n
    return out


def permutation_test(
    x: np.ndarray,
    y: np.ndarray,
    stat_fn: Callable[[np.ndarray, np.ndarray], float],
    n_perm: int = 10_000,
    seed: int = 0,
) -> dict[str, float]:
    """Two-sample permutation test.

    Shuffles labels between x and y ``n_perm`` times, keeping the combined sample
    fixed, and constructs the empirical null distribution of ``stat_fn``.
    """
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    combined = np.concatenate([x, y])
    n_x = len(x)
    observed = stat_fn(x, y)
    null = np.empty(n_perm, dtype=float)
    for i in range(n_perm):
        perm = rng.permutation(combined)
        null[i] = stat_fn(perm[:n_x], perm[n_x:])
    # two-sided empirical p-value
    p = (np.sum(np.abs(null) >= abs(observed)) + 1.0) / (n_perm + 1.0)
    return {
        "observed": float(observed),
        "p_value": float(p),
        "n_perm": n_perm,
        "null_mean": float(np.mean(null)),
    }