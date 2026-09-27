"""Streaming tick ingestion and multi-timeframe OHLCV aggregator for QROS.

Ingests raw millisecond-level tick CSV payloads in memory-safe streaming chunks,
constructs exact point-in-time Bid OHLCV bars with dynamic spread and volume,
and resamples into M1, M5, H1, and D1 institutional Parquet datasets (v4.0.0).
"""

from datetime import datetime
import json
import logging
import os
import sys
import time
from typing import Dict

import numpy as np
import pandas as pd

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from qros.data.quality import audit_dataset_quality
from qros.data.splitting import DataSplitter
from qros.data.validation import compute_dataset_hash
from qros.data.vault.oos_vault import ProtectedOOSVault

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("QROS.Ingestion.Ticks")


def process_tick_stream_to_m1(
    tick_file_path: str,
    chunk_size: int = 3_000_000,
    point_multiplier: float = 100.0,
    cache_path: str = "data/processed/xauusd/m1_tick_cache.parquet",
) -> pd.DataFrame:
    """Stream process millisecond ticks into a continuous 1-minute (M1) OHLCV DataFrame."""
    if os.path.exists(cache_path):
        logger.info(f"Loading cached M1 dataset from: {cache_path}")
        return pd.read_parquet(cache_path)

    logger.info(f"Opening tick stream from: {tick_file_path}")
    if not os.path.exists(tick_file_path):
        raise FileNotFoundError(f"Tick file not found: {tick_file_path}")

    start_time = time.time()
    m1_chunks = []
    total_ticks = 0
    chunk_idx = 0

    last_bid = np.nan
    last_ask = np.nan

    for chunk in pd.read_csv(
        tick_file_path,
        sep="\t",
        chunksize=chunk_size,
        dtype={
            "<DATE>": str,
            "<TIME>": str,
            "<BID>": float,
            "<ASK>": float,
            "<LAST>": float,
            "<VOLUME>": float,
            "<FLAGS>": float,
        },
    ):
        chunk_idx += 1
        total_ticks += len(chunk)

        # 1. Parse timestamps
        dt_series = pd.to_datetime(
            chunk["<DATE>"] + " " + chunk["<TIME>"],
            format="%Y.%m.%d %H:%M:%S.%f",
            utc=True,
        )

        # 2. Forward fill Bid & Ask
        bids = chunk["<BID>"].copy()
        asks = chunk["<ASK>"].copy()

        if not np.isnan(last_bid) and np.isnan(bids.iloc[0]):
            bids.iloc[0] = last_bid
        if not np.isnan(last_ask) and np.isnan(asks.iloc[0]):
            asks.iloc[0] = last_ask

        bids = bids.ffill().bfill()
        asks = asks.ffill().bfill()

        last_bid = bids.iloc[-1]
        last_ask = asks.iloc[-1]

        spread_pts = ((asks - bids) * point_multiplier).clip(lower=0, upper=5000)

        # 3. Intermediate 1-minute aggregation
        df_tick = pd.DataFrame(
            {"bid": bids.values, "spread_pts": spread_pts.values},
            index=dt_series,
        )

        m1_agg = df_tick.resample("1min").agg(
            open=("bid", "first"),
            high=("bid", "max"),
            low=("bid", "min"),
            close=("bid", "last"),
            tick_volume=("bid", "count"),
            spread_pts=("spread_pts", "mean"),
        )

        m1_agg = m1_agg[m1_agg["tick_volume"] > 0]
        m1_chunks.append(m1_agg)

        elapsed = time.time() - start_time
        rate = total_ticks / elapsed if elapsed > 0 else 0
        logger.info(
            f"Chunk {chunk_idx:3d}: Processed {total_ticks:11,d} ticks "
            f"({rate:9.0f} ticks/s) | M1 bar buffer: {sum(len(c) for c in m1_chunks):,d}"
        )

    logger.info("Consolidating M1 bars across chunk boundaries...")
    df_m1_raw = pd.concat(m1_chunks)

    df_m1 = df_m1_raw.groupby(df_m1_raw.index).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        spread_pts=("spread_pts", "mean"),
    )

    df_m1["spread_pts"] = df_m1["spread_pts"].round().astype(int)
    df_m1["real_volume"] = 0
    df_m1.index.name = "timestamp"

    total_time = time.time() - start_time
    logger.info(f"M1 Processing Complete: {total_ticks:,d} ticks -> {len(df_m1):,d} M1 bars in {total_time:.2f}s")
    
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df_m1.to_parquet(cache_path, engine="pyarrow")
    logger.info(f"Saved M1 cache to: {cache_path}")
    return df_m1


def resample_m1_to_timeframes(df_m1: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Resample M1 bars into M5, H1, and D1 OHLCV datasets."""
    logger.info("Resampling M1 dataset to M5, H1, and D1...")

    df_m5 = df_m1.resample("5min").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        spread_pts=("spread_pts", "mean"),
        real_volume=("real_volume", "first"),
    ).dropna(subset=["open"])
    df_m5["spread_pts"] = df_m5["spread_pts"].round().astype(int)
    df_m5.index.name = "timestamp"

    df_h1 = df_m1.resample("1h").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        spread_pts=("spread_pts", "mean"),
        real_volume=("real_volume", "first"),
    ).dropna(subset=["open"])
    df_h1["spread_pts"] = df_h1["spread_pts"].round().astype(int)
    df_h1.index.name = "timestamp"

    df_d1 = df_m1.resample("1D").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        spread_pts=("spread_pts", "mean"),
        real_volume=("real_volume", "first"),
    ).dropna(subset=["open"])
    df_d1["spread_pts"] = df_d1["spread_pts"].round().astype(int)
    df_d1.index.name = "timestamp"

    logger.info(f"Resampling complete: M1={len(df_m1):,d}, M5={len(df_m5):,d}, H1={len(df_h1):,d}, D1={len(df_d1):,d}")

    return {
        "M1": df_m1,
        "M5": df_m5,
        "H1": df_h1,
        "D1": df_d1,
    }


def execute_v4_ingestion_pipeline(
    tick_file_path: str,
    output_dir: str = "data/processed/xauusd",
    vault_dir: str = "data/vault/xauusd",
    version: str = "v4.0.0",
) -> None:
    """Execute complete Stage 3 audit, 4-tier partitioning, and Protected OOS vaulting."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(vault_dir, exist_ok=True)

    df_m1 = process_tick_stream_to_m1(tick_file_path)
    datasets = resample_m1_to_timeframes(df_m1)

    splitter = DataSplitter(eda_pct=0.20, train_pct=0.40, val_pct=0.20, oos_pct=0.20)
    vault = ProtectedOOSVault(vault_directory=vault_dir)

    manifest_entries = []

    print("\n" + "=" * 80)
    print(f"QROS STAGE 3 DATA QUALITY & VAULT AUDIT — DATASET VERSION {version}")
    print("=" * 80)

    for tf, df in datasets.items():
        dataset_id = f"QROS-DATA-XAUUSD-{tf}-{version}"
        clean_filename = f"xauusd_{tf.lower()}_full_clean_{version}.parquet"
        clean_path = os.path.join(output_dir, clean_filename)

        quality_report = audit_dataset_quality(df, symbol="XAUUSD", timeframe=tf, dataset_version=version)
        status_str = quality_report.overall_approval_status
        print(
            f"[{tf}] Bars: {len(df):8,d} | Span: {quality_report.start_timestamp[:10]} -> {quality_report.end_timestamp[:10]} | Status: {status_str}"
        )

        if status_str != "APPROVED":
            raise ValueError(f"Dataset {dataset_id} failed Stage 3 Quality Audit: {quality_report.detected_anomalies}")

        df.to_parquet(clean_path, engine="pyarrow", compression="snappy")
        full_hash = compute_dataset_hash(df)

        split_res = splitter.split(df)

        t1_path = os.path.join(output_dir, f"xauusd_{tf.lower()}_{version}_tier1_eda.parquet")
        t2_path = os.path.join(output_dir, f"xauusd_{tf.lower()}_{version}_tier2_train.parquet")
        t3_path = os.path.join(output_dir, f"xauusd_{tf.lower()}_{version}_tier3_val.parquet")

        split_res.eda.to_parquet(t1_path, engine="pyarrow")
        split_res.train.to_parquet(t2_path, engine="pyarrow")
        split_res.validation.to_parquet(t3_path, engine="pyarrow")

        vault_filename = f"qros-data-xauusd-{tf.lower()}-{version}_tier4_oos.parquet"
        vault_path = os.path.join(vault_dir, vault_filename)
        split_res._oos.to_parquet(vault_path, engine="pyarrow")

        t4_hash = compute_dataset_hash(split_res._oos)

        manifest_entries.append(
            {
                "dataset_id": dataset_id,
                "asset": "XAUUSD",
                "timeframe": tf,
                "version": version,
                "total_bars": len(df),
                "start_timestamp": str(df.index[0]),
                "end_timestamp": str(df.index[-1]),
                "sha256": full_hash,
                "tier4_oos_sha256": t4_hash,
                "quality_status": status_str,
            }
        )

    manifest_path = "docs/research/data/DATASET_MANIFEST.json"
    existing_manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as fp:
            existing_manifest = json.load(fp)

    existing_manifest[f"xauusd_{version}"] = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "source": "Institutional Tick CSV Ingestion (6.15 Years)",
        "datasets": manifest_entries,
    }

    with open(manifest_path, "w") as fp:
        json.dump(existing_manifest, fp, indent=2)

    print("\n" + "=" * 80)
    print("INGESTION, STAGE 3 AUDIT & OOS VAULTING COMPLETED SUCCESSFULLY!")
    print(f"Master manifest updated: {manifest_path}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    tick_file = r"C:\Users\adhik\OneDrive\Desktop\QROS\xauusd\XAUUSD_202007011200_202608251048.csv"
    execute_v4_ingestion_pipeline(tick_file)