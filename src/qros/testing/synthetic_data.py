"""Synthetic dataset generators and controlled mathematical distribution fixtures for QROS testing.

Guarantees 100% synthetic, deterministic data generation with zero real market data.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


def generate_synthetic_ohlcv(
    n_bars: int = 1000,
    start_time: str = "2023-01-01 00:00:00",
    freq: str = "5min",
    initial_price: float = 1800.0,
    annualized_volatility: float = 0.15,
    annualized_drift: float = 0.05,
    spread_pts: float = 20.0,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Generate a clean synthetic OHLCV time-series using Geometric Brownian Motion (GBM).

    Parameters
    ----------
    n_bars : int
        Number of bars to simulate.
    start_time : str
        Start timestamp (UTC).
    freq : str
        Pandas frequency string (e.g. '1min', '5min', '1h', '1D').
    initial_price : float
        Starting price.
    annualized_volatility : float
        Annualized standard deviation of returns.
    annualized_drift : float
        Annualized expected return.
    spread_pts : float
        Synthetic bid-ask spread in points.
    random_seed : int
        Deterministic random seed.

    Returns
    -------
    pd.DataFrame
        Clean synthetic OHLCV dataframe with strictly monotonic UTC DatetimeIndex.
    """
    rng = np.random.default_rng(random_seed)
    timestamps = pd.date_range(start_time, periods=n_bars, freq=freq, tz="UTC")

    # Time delta in years per bar
    total_seconds_per_year = 365.25 * 86400.0
    bar_seconds = (timestamps[1] - timestamps[0]).total_seconds() if n_bars > 1 else 300.0
    dt = bar_seconds / total_seconds_per_year

    # Simulate log returns via GBM: dlnS = (mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z
    mu = annualized_drift
    sigma = annualized_volatility
    drift = (mu - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt)

    shocks = rng.normal(loc=0.0, scale=1.0, size=n_bars)
    log_rets = drift + diffusion * shocks
    log_rets[0] = 0.0

    # Path of close prices
    log_prices = np.log(initial_price) + np.cumsum(log_rets)
    close_prices = np.exp(log_prices)

    # Intrabar price movements
    intrabar_vol = diffusion * close_prices * 0.75
    open_prices = np.empty(n_bars, dtype=np.float64)
    open_prices[0] = initial_price
    open_prices[1:] = close_prices[:-1]  # Standard continuous market open = prev close

    # Random intrabar noise for high and low
    u1 = np.abs(rng.normal(loc=0.0, scale=1.0, size=n_bars)) * intrabar_vol
    u2 = np.abs(rng.normal(loc=0.0, scale=1.0, size=n_bars)) * intrabar_vol

    high_prices = np.maximum(open_prices, close_prices) + u1
    low_prices = np.minimum(open_prices, close_prices) - u2

    # Ensure strictly low > 0
    low_prices = np.maximum(0.01, low_prices)

    # Synthetic volume (log-normal distribution)
    volume = np.exp(rng.normal(loc=5.5, scale=0.8, size=n_bars)).astype(int) + 50

    df = pd.DataFrame(
        {
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "volume": volume,
        },
        index=timestamps,
    )
    return df


def generate_fat_tailed_returns(
    n_samples: int = 2000,
    df_degrees: float = 4.0,
    loc: float = 0.001,
    scale: float = 0.015,
    random_seed: int = 42,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Generate fat-tailed return series from Student-t distribution with known theoretical moments.

    For Student-t with degrees of freedom nu > 4:
    - Mean = loc
    - Variance = scale^2 * (nu / (nu - 2))
    - Skewness = 0.0
    - Excess Kurtosis = 6 / (nu - 4)
    """
    rng = np.random.default_rng(random_seed)
    raw_t = rng.standard_t(df=df_degrees, size=n_samples)
    returns = loc + scale * raw_t

    theoretical_var = (scale**2) * (df_degrees / (df_degrees - 2.0))
    theoretical_std = np.sqrt(theoretical_var)
    theoretical_kurtosis = 6.0 / (df_degrees - 4.0) if df_degrees > 4.0 else float("inf")

    moments_info = {
        "theoretical_mean": loc,
        "theoretical_std": theoretical_std,
        "theoretical_skewness": 0.0,
        "theoretical_excess_kurtosis": theoretical_kurtosis,
        "df_degrees": df_degrees,
    }
    return returns, moments_info


def generate_autocorrelated_series(
    n_samples: int = 2000,
    ar_phi: float = 0.6,
    sigma_eps: float = 0.01,
    random_seed: int = 42,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Generate stationary AR(1) return series: X_t = phi * X_{t-1} + eps_t.

    Theoretical properties:
    - Autocorrelation at lag k: rho(k) = phi^k
    - Theoretical effective sample size: N_eff = N * (1 - phi) / (1 + phi)
    """
    rng = np.random.default_rng(random_seed)
    eps = rng.normal(0, sigma_eps, size=n_samples)
    series = np.empty(n_samples, dtype=np.float64)
    series[0] = eps[0] / np.sqrt(1 - ar_phi**2)  # Stationary initialization

    for t in range(1, n_samples):
        series[t] = ar_phi * series[t - 1] + eps[t]

    theoretical_neff = n_samples * (1.0 - ar_phi) / (1.0 + ar_phi)

    info = {
        "ar_phi": ar_phi,
        "theoretical_rho_1": ar_phi,
        "theoretical_rho_2": ar_phi**2,
        "theoretical_neff": theoretical_neff,
    }
    return series, info


def generate_corrupted_dataset(
    corruption_type: str = "high_low_violation",
    n_bars: int = 100,
) -> pd.DataFrame:
    """Generate an OHLCV dataset with intentionally injected anomalies for adversarial testing.

    Supported corruption_type:
    - 'high_low_violation': High < Low on random bars
    - 'negative_price': Negative price values
    - 'nan_values': Injected NaNs
    - 'infinite_values': Injected infinities
    - 'non_monotonic_time': Shuffled/backward timestamps
    - 'duplicate_timestamps': Repeated timestamps
    - 'timezone_naive': Non-UTC naive DatetimeIndex
    """
    df = generate_synthetic_ohlcv(n_bars=n_bars, random_seed=42)

    if corruption_type == "high_low_violation":
        df.loc[df.index[10], "high"] = df.loc[df.index[10], "low"] - 5.0
    elif corruption_type == "negative_price":
        df.loc[df.index[15], "close"] = -100.0
    elif corruption_type == "nan_values":
        df.loc[df.index[20], "open"] = np.nan
    elif corruption_type == "infinite_values":
        df.loc[df.index[25], "close"] = np.inf
    elif corruption_type == "non_monotonic_time":
        shuffled_idx = list(df.index)
        shuffled_idx[10], shuffled_idx[11] = shuffled_idx[11], shuffled_idx[10]
        df.index = shuffled_idx
    elif corruption_type == "duplicate_timestamps":
        dup_idx = list(df.index)
        dup_idx[10] = dup_idx[9]
        df.index = dup_idx
    elif corruption_type == "timezone_naive":
        df.index = df.index.tz_localize(None)
    else:
        raise ValueError(f"Unknown corruption_type: {corruption_type}")

    return df
