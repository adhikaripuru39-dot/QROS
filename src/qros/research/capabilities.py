"""Data Capability and Sufficiency Auditor across Quantitative Research Classes I–V."""

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple
import pandas as pd


@dataclass
class ClassSufficiencyResult:
    """Sufficiency evaluation outcome for a specific Quantitative Research Class."""

    research_class: str
    class_name: str
    target_timeframe: str
    available_observations: int
    required_observations: int
    available_span_years: float
    required_span_years: float
    is_sufficient: bool
    status_label: str  # SUFFICIENT / DATA INSUFFICIENT
    notes: str


def evaluate_data_sufficiency(
    data_map: Dict[str, pd.DataFrame],
) -> Dict[str, ClassSufficiencyResult]:
    """Audit available research partitions against the 5 Quantitative Research Classes.

    Parameters
    ----------
    data_map : Dict[str, pd.DataFrame]
        Map of timeframe string ('M1', 'M5', 'H1', 'D1') to non-OOS dataframe.

    Returns
    -------
    Dict[str, ClassSufficiencyResult]
        Sufficiency evaluation by research class.
    """
    results = {}

    # Class I: High-Frequency Microstructure (HF-MICRO) -> Target: M1/M5
    df_m1 = data_map.get("M1", pd.DataFrame())
    n_m1 = len(df_m1)
    span_m1 = (
        (df_m1.index[-1] - df_m1.index[0]).total_seconds() / (365.25 * 86400.0)
        if n_m1 > 1
        else 0.0
    )
    req_n_c1 = 1000
    req_span_c1 = 0.02  # ~1 week
    suff_c1 = n_m1 >= req_n_c1 and span_m1 >= req_span_c1
    results["CLASS-I"] = ClassSufficiencyResult(
        research_class="CLASS-I",
        class_name="High-Frequency Microstructure (HF-MICRO)",
        target_timeframe="M1",
        available_observations=n_m1,
        required_observations=req_n_c1,
        available_span_years=span_m1,
        required_span_years=req_span_c1,
        is_sufficient=suff_c1,
        status_label="SUFFICIENT" if suff_c1 else "DATA INSUFFICIENT",
        notes="Sufficient for intraday microstructural spread/volume analysis and rapid execution dynamics.",
    )

    # Class II: Intraday Momentum & Breakout (INTRADAY-MOM) -> Target: M5
    df_m5 = data_map.get("M5", pd.DataFrame())
    n_m5 = len(df_m5)
    span_m5 = (
        (df_m5.index[-1] - df_m5.index[0]).total_seconds() / (365.25 * 86400.0)
        if n_m5 > 1
        else 0.0
    )
    req_n_c2 = 400
    req_span_c2 = 0.10  # ~1.2 months
    suff_c2 = n_m5 >= req_n_c2 and span_m5 >= req_span_c2
    results["CLASS-II"] = ClassSufficiencyResult(
        research_class="CLASS-II",
        class_name="Intraday Momentum & Breakout (INTRADAY-MOM)",
        target_timeframe="M5",
        available_observations=n_m5,
        required_observations=req_n_c2,
        available_span_years=span_m5,
        required_span_years=req_span_c2,
        is_sufficient=suff_c2,
        status_label="SUFFICIENT" if suff_c2 else "DATA INSUFFICIENT",
        notes="Sufficient for session breakout, diurnal volatility expansion, and intraday momentum modeling.",
    )

    # Class III: Swing & Statistical Arbitrage (SWING-STATARB) -> Target: H1
    df_h1 = data_map.get("H1", pd.DataFrame())
    n_h1 = len(df_h1)
    span_h1 = (
        (df_h1.index[-1] - df_h1.index[0]).total_seconds() / (365.25 * 86400.0)
        if n_h1 > 1
        else 0.0
    )
    req_n_c3 = 150
    req_span_c3 = 1.0  # 1 year
    suff_c3 = n_h1 >= req_n_c3 and span_h1 >= req_span_c3
    results["CLASS-III"] = ClassSufficiencyResult(
        research_class="CLASS-III",
        class_name="Swing & Statistical Arbitrage (SWING-STATARB)",
        target_timeframe="H1",
        available_observations=n_h1,
        required_observations=req_n_c3,
        available_span_years=span_h1,
        required_span_years=req_span_c3,
        is_sufficient=suff_c3,
        status_label="SUFFICIENT" if suff_c3 else "DATA INSUFFICIENT",
        notes="Sufficient for multi-day swing structure, volatility clustering, and mean reversion modeling.",
    )

    # Class IV: Macro Regime & Trend (MACRO-REGIME) -> Target: D1
    df_d1 = data_map.get("D1", pd.DataFrame())
    n_d1 = len(df_d1)
    span_d1 = (
        (df_d1.index[-1] - df_d1.index[0]).total_seconds() / (365.25 * 86400.0)
        if n_d1 > 1
        else 0.0
    )
    req_n_c4 = 3000
    req_span_c4 = 12.0  # 12 years (2 full business cycles)
    suff_c4 = n_d1 >= req_n_c4 and span_d1 >= req_span_c4
    results["CLASS-IV"] = ClassSufficiencyResult(
        research_class="CLASS-IV",
        class_name="Macro Regime & Trend (MACRO-REGIME)",
        target_timeframe="D1",
        available_observations=n_d1,
        required_observations=req_n_c4,
        available_span_years=span_d1,
        required_span_years=req_span_c4,
        is_sufficient=suff_c4,
        status_label="SUFFICIENT" if suff_c4 else "DATA INSUFFICIENT",
        notes=f"Available D1 history ({span_d1:.2f} years, {n_d1} bars) is insufficient for full 12-year multi-cycle macro validation. Exploratory fact discovery is permissible; formal macro certification requires additional historical data.",
    )

    # Class V: Structural Arbitrage & Cross-Asset Relative Value (CROSS-ASSET-STRUCTURAL)
    results["CLASS-V"] = ClassSufficiencyResult(
        research_class="CLASS-V",
        class_name="Cross-Asset Structural Arbitrage (CROSS-ASSET-STRUCTURAL)",
        target_timeframe="Cross-Asset",
        available_observations=0,
        required_observations=200,
        available_span_years=0.0,
        required_span_years=2.0,
        is_sufficient=False,
        status_label="DATA INSUFFICIENT",
        notes="Requires simultaneous synchronized feeds for secondary assets (e.g. XAGUSD, DXY, US10Y). Currently only single-asset XAUUSD is ingested.",
    )

    return results
