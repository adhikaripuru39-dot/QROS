"""Multiple testing correction and False Discovery Rate (FDR) adjustments."""

from typing import List, Tuple
import numpy as np


def benjamini_hochberg(
    p_values: List[float], fdr_q: float = 0.05
) -> Tuple[np.ndarray, np.ndarray]:
    """Execute Benjamini-Hochberg procedure controlling the False Discovery Rate (FDR).

    Parameters
    ----------
    p_values : List[float]
        List or array of raw p-values from multiple hypothesis tests.
    fdr_q : float
        Target False Discovery Rate threshold (default: 0.05).

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        - Boolean array (is_significant) indicating rejected null hypotheses.
        - Array of adjusted p-values (q-values).
    """
    p_arr = np.asarray(p_values, dtype=np.float64)
    m = len(p_arr)
    if m == 0:
        return np.array([], dtype=bool), np.array([], dtype=np.float64)

    # Sort p-values ascending
    sorted_indices = np.argsort(p_arr)
    sorted_p = p_arr[sorted_indices]

    # Compute BH critical thresholds: (i / m) * q
    ranks = np.arange(1, m + 1)
    bh_thresholds = (ranks / float(m)) * fdr_q

    # Find the largest k where p_(k) <= (k/m)*q
    significant_mask = sorted_p <= bh_thresholds
    if np.any(significant_mask):
        max_sig_idx = np.max(np.where(significant_mask)[0])
        sig_sorted = np.zeros(m, dtype=bool)
        sig_sorted[: max_sig_idx + 1] = True
    else:
        sig_sorted = np.zeros(m, dtype=bool)

    # Calculate adjusted p-values (q-values)
    # q_i = min_{j >= i} (m / j * p_(j))
    q_values_sorted = np.empty(m, dtype=np.float64)
    running_min = 1.0
    for i in range(m - 1, -1, -1):
        val = (float(m) / ranks[i]) * sorted_p[i]
        running_min = min(running_min, val)
        q_values_sorted[i] = min(1.0, running_min)

    # Re-order to original sequence
    reordered_sig = np.empty(m, dtype=bool)
    reordered_sig[sorted_indices] = sig_sorted

    reordered_q = np.empty(m, dtype=np.float64)
    reordered_q[sorted_indices] = q_values_sorted

    return reordered_sig, reordered_q


def bonferroni_correction(
    p_values: List[float], alpha: float = 0.05
) -> Tuple[np.ndarray, np.ndarray]:
    """Execute standard Bonferroni Family-Wise Error Rate (FWER) correction.

    Adjusted p-value = min(1.0, p * m).
    """
    p_arr = np.asarray(p_values, dtype=np.float64)
    m = len(p_arr)
    if m == 0:
        return np.array([], dtype=bool), np.array([], dtype=np.float64)

    adj_p = np.minimum(1.0, p_arr * float(m))
    sig = adj_p <= alpha
    return sig, adj_p
