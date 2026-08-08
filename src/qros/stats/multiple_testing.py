"""Part 8 ch.1: Multiple testing corrections — FDR-BH and FWER-Holm."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from qros.governance.policy import DEFAULT_POLICY, Policy


def benjamini_hochberg(p: Sequence[float], q: float | None = None, policy: Policy = DEFAULT_POLICY) -> tuple[np.ndarray, float]:
    """Benjamini-Hochberg FDR control.

    Returns ``(reject_mask, q_used)`` where reject_mask[i] is True when
    p_(i) <= (i/N) * q (FDR q* <= 0.05).
    """
    q = DEFAULT_POLICY.fdr_q_max if q is None else q
    p = np.asarray(p, dtype=float)
    n = len(p)
    if n == 0:
        return np.zeros(0, dtype=bool), q
    order = np.argsort(p)
    sorted_p = p[order]
    thresholds = np.arange(1, n + 1) / n * q
    passed = (sorted_p <= thresholds) & np.isfinite(sorted_p)
    reject = np.zeros(n, dtype=bool)
    if passed.any():
        max_idx = np.where(passed)[0].max()
        reject[order[: max_idx + 1]] = True
    return reject, q


def holm_bonferroni(p: Sequence[float], alpha: float = DEFAULT_POLICY.holm_alpha) -> tuple[np.ndarray, float]:
    """Holm-Bonferroni FWER control (alpha = 0.01).

    Reject sorted p_(i) when p_(i) <= alpha / (N - i + 1),
    halting at the first non-rejection (sequential gate).
    """
    p = np.asarray(p, dtype=float)
    n = len(p)
    reject = np.zeros(n, dtype=bool)
    if n == 0:
        return reject, alpha
    order = np.argsort(p)
    sorted_p = p[order]
    # Holm: reject p_(i) if p_(i) <= alpha / (N - i + 1);
    # sequential gate: once a sorted test fails, all later fail.
    k = 0
    for i in range(n):
        if sorted_p[i] <= alpha / (n - i):
            k = i + 1
        else:
            break
    reject[order[:k]] = True
    return reject, alpha