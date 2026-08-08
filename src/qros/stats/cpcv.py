"""Part 8 ch.1: Combinatorial Purged Cross-Validation (CPCV).

Handbook parameters:
- purging gap = max_holding (leakage from overlapping labels)
- embargo = 1% of total sample
- number of paths N_paths >= 16
- Probability of Backtest Overfitting (PBO) < 0.10
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from qros.governance.policy import DEFAULT_POLICY, Policy


def split_leaves(
    T: int,
    n_splits: int,
    k_test: int,
    purge: int = 0,
    embargo: float = 0.01,
    rng: np.random.Generator | None = None,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Generate (train_idx, test_idx) pairs for all CPCV combinations.

    Splits ``T`` observations into ``n_splits`` contiguous test groups; for each
    combination of ``k_test`` groups forming a test block, the train set is the
    complement, purged by ``purge`` observations either side of the test block and
    an embargo of ``embargo`` fraction of T.
    """
    n_leaves = int(T / n_splits)
    split_points = np.arange(0, T, n_leaves)[:n_splits]
    groups = [np.arange(a, min(a + n_leaves, T)) for a in split_points]
    embargo_size = int(embargo * T)
    results: list[tuple[np.ndarray, np.ndarray]] = []
    for combo in itertools.combinations(range(n_splits), k_test):
        test_idx = np.concatenate([groups[c] for c in combo])
        test_lo, test_hi = int(test_idx.min()), int(test_idx.max())
        # purge gap around the test block
        train_mask = np.ones(T, dtype=bool)
        train_mask[test_lo : test_hi + 1] = False
        # purge on either side
        train_mask[max(0, test_lo - purge) : test_lo] = False
        train_mask[test_hi + 1 : min(T, test_hi + 1 + purge)] = False
        # embargo after the test block
        train_mask[test_hi + 1 : min(T, test_hi + 1 + embargo_size)] = False
        train_idx = np.where(train_mask)[0]
        results.append((train_idx, test_idx))
    return results


@dataclass
class CPCVResult:
    paths: int
    n_splits: int
    pbo: float
    n_train_obs: int
    n_test_obs: int
    pass_criteria: bool


def _sharpe(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2 or np.std(x) == 0:
        return 0.0
    return float(np.mean(x) / np.std(x) * np.sqrt(len(x)))


def pbo_from_matrices(is_sr: np.ndarray, oos_sr: np.ndarray, rng: np.random.Generator | None = None) -> float:
    """Probability of Backtest Overfitting (Bailey et al.).

    For each path, rank the IS Sharpe and compute the rank of the corresponding
    OOS Sharpe; PBO is the frequency (across paths) of observing a rank below the
    median IS rank.
    """
    is_sr = np.asarray(is_sr, dtype=float)
    oos_sr = np.asarray(oos_sr, dtype=float)
    n = len(is_sr)
    if n < 2:
        return 0.0
    is_ranks = np.argsort(np.argsort(is_sr)) + 1  # 1..n
    median_is = float(np.median(is_ranks))
    oos_for_rank = np.empty(n)
    for i in range(n):
        r = is_ranks[i]
        oos_for_rank[r - 1] = oos_sr[i]
    below = np.mean(oos_for_rank < median_is)
    return float(below)


def combinatorial_purged_cv(
    returns: np.ndarray,
    n_splits: int = 8,
    k_test: int = 2,
    purge: int = 0,
    policy: Policy = DEFAULT_POLICY,
    seed: int = 0,
) -> CPCVResult:
    """Run CPCV over a return series; report paths, PBO and gate compliance.

    Fits a trivial "edge" (the series itself) — the split structure and PBO
    computation are the tested deliverable; downstream pipelines substitute
    their own IS/OOS fits via ``split_leaves``. Default (8,2) yields
    C(8,2)=28 paths >= 16 required by the handbook.
    """
    rng = np.random.default_rng(seed)
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    T = len(returns)
    if T == 0:
        return CPCVResult(paths=0, n_splits=n_splits, pbo=0.0, n_train_obs=0, n_test_obs=0, pass_criteria=False)
    pairs = split_leaves(T, n_splits, k_test, purge=purge, embargo=policy.cpcv_embargo_pct, rng=rng)
    is_sr: list[float] = []
    oos_sr: list[float] = []
    n_train, n_test = 0, 0
    for train_idx, test_idx in pairs:
        is_sr.append(_sharpe(returns[train_idx]))
        oos_sr.append(_sharpe(returns[test_idx]))
        n_train = max(n_train, len(train_idx))
        n_test = max(n_test, len(test_idx))
    paths = len(pairs)
    pbo = pbo_from_matrices(np.array(is_sr), np.array(oos_sr), rng) if paths else 0.0
    pass_criteria = paths >= policy.cpcv_min_paths and pbo < policy.pbo_max
    return CPCVResult(
        paths=paths,
        n_splits=n_splits,
        pbo=pbo,
        n_train_obs=n_train,
        n_test_obs=n_test,
        pass_criteria=pass_criteria,
    )