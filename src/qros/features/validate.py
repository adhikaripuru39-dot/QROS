"""Part 4 ch.3: Feature validation & leakage prevention — ADF, VIF, correlation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from qros.governance.policy import DEFAULT_POLICY, Policy


@dataclass
class StationarityResult:
    p: float
    passed: bool


def adf_pvalue(x, maxlag: int | None = None, autolag: str = "AIC") -> float:
    """Augmented Dickey-Fuller p-value via statsmodels."""
    arr = np.asarray(x, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 4:
        return float("nan")
    result = adfuller(arr, maxlag=maxlag, autolag=autolag)
    return float(result[1])


def test_stationarity(x, policy: Policy = DEFAULT_POLICY) -> StationarityResult:
    p = adf_pvalue(x)
    return StationarityResult(p=p, passed=bool(np.isfinite(p) and p < policy.adf_p_max))


def vif_table(df: pd.DataFrame) -> pd.Series:
    """Variance Inflation Factor per feature."""
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    mask = np.isfinite(df.to_numpy(dtype=float)).all(axis=1)
    X = df[mask].dropna()
    if X.empty or X.shape[1] == 0:
        return pd.Series(dtype=float)
    Xc = X.copy()
    Xc["_const"] = 1.0
    vif: dict[str, float] = {}
    for i, col in enumerate(X.columns):
        try:
            vif[col] = float(variance_inflation_factor(Xc.values, i))
        except Exception:
            vif[col] = float("nan")
    return pd.Series(vif)


def detect_multicollinearity(df: pd.DataFrame, policy: Policy = DEFAULT_POLICY) -> list[str]:
    """Columns whose variance inflation factor exceeds ``policy.vif_max``."""
    if df.shape[1] <= 1:
        return []
    vif = vif_table(df)
    return [c for c in vif.index if np.isfinite(vif[c]) and vif[c] > policy.vif_max]


def correlation_filter(df: pd.DataFrame, policy: Policy = DEFAULT_POLICY) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Drop features with |corr| > policy.corr_max; return (kept frame, dropped pairs)."""
    if df.shape[1] <= 1:
        return df, []
    corr = df.corr().abs()
    keep: list[str] = list(df.columns)
    dropped: list[tuple[str, str]] = []
    for i, a in enumerate(df.columns):
        for b in df.columns[i + 1 :]:
            if a not in keep or b not in keep:
                continue
            value = corr.loc[a, b]
            if isinstance(value, (int, float)) and abs(value) > policy.corr_max:
                dropped.append((a, b))
                # keep the first-seen column, drop the later one
                if b in keep:
                    keep.remove(b)
    return df[keep], dropped


@dataclass
class ValidationReport:
    stationarity: dict[str, StationarityResult]
    vif: pd.Series
    dropped: list[str]
    correlation_pairs: list[tuple[str, str]]

    def all_stationary(self) -> bool:
        return all(r.passed for r in self.stationarity.values())

    def max_adf_p(self) -> float:
        return max((r.p for r in self.stationarity.values()), default=float("nan"))


def validate_feature_frame(df: pd.DataFrame, policy: Policy = DEFAULT_POLICY) -> ValidationReport:
    """Run ADF stationarity, multicollinearity (VIF) and correlation filters."""
    stationarity: dict[str, StationarityResult] = {
        col: test_stationarity(df[col], policy) for col in df.columns
    }
    dropped = detect_multicollinearity(df, policy)
    kept, corr_pairs = correlation_filter(df, policy)
    dropped = list(set(dropped).union(set(df.columns) - set(kept.columns)))
    return ValidationReport(
        stationarity=stationarity,
        vif=vif_table(df),
        dropped=dropped,
        correlation_pairs=corr_pairs,
    )