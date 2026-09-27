"""Unit tests for Benjamini-Hochberg FDR and Bonferroni corrections."""

import numpy as np
import pytest
from qros.stats.multiple_testing import (
    benjamini_hochberg,
    bonferroni_correction,
)


def test_benjamini_hochberg_fdr():
    # 10 hypotheses with mixed p-values
    p_vals = [0.001, 0.005, 0.01, 0.03, 0.04, 0.20, 0.45, 0.60, 0.80, 0.95]
    sig, q_vals = benjamini_hochberg(p_vals, fdr_q=0.05)

    assert len(sig) == 10
    assert len(q_vals) == 10
    # The smallest p-values should be rejected
    assert sig[0] == True
    assert sig[1] == True
    # The large p-values must not be rejected
    assert sig[-1] == False
    assert q_vals[-1] >= 0.95


def test_bonferroni_correction():
    p_vals = [0.001, 0.01, 0.04, 0.05]
    # m = 4, alpha = 0.05 -> critical value 0.05 / 4 = 0.0125
    sig, adj_p = bonferroni_correction(p_vals, alpha=0.05)

    assert sig[0] == True  # 0.001 * 4 = 0.004 <= 0.05
    assert sig[1] == True  # 0.01 * 4 = 0.04 <= 0.05
    assert sig[2] == False  # 0.04 * 4 = 0.16 > 0.05
    assert sig[3] == False  # 0.05 * 4 = 0.20 > 0.05
