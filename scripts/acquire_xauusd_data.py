"""Acquisition, normalization, quality audit, and vaulted partitioning of XAUUSD research datasets."""

import os
from datetime import datetime, timezone
import pandas as pd
from qros.data.adapters.mt5_adapter import MT5IngestionAdapter
from qros.data.quality import audit_dataset_quality
from qros.data.splitting import DataSplitter
from qros.data.validation import compute_dataset_hash
from qros.data.vault.manifest import (
    DatasetManifest,
    DatasetRegistry,
    PartitionInfo,
)
from qros.data.vault.oos_vault import ProtectedOOSVault


def main():
    print("=== Starting QROS Real Market Data Acquisition (XAUUSD) ===")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_raw_dir = os.path.join(base_dir, "data", "raw", "xauusd")
    data_proc_dir = os.path.join(base_dir, "data", "processed", "xauusd")
    data_vault_dir = os.path.join(base_dir, "data", "vault", "xauusd")
    docs_data_dir = os.path.join(base_dir, "docs", "research", "data")

    for d in [data_raw_dir, data_proc_dir, data_vault_dir, docs_data_dir]:
        os.makedirs(d, exist_ok=True)

    adapter = MT5IngestionAdapter()
    print("MT5 Adapter availability:", adapter.is_available(), flush=True)

    # Target resolutions to ingest
    resolutions = [
        ("M5", 5000),   # 5,000 M5 bars
        ("H1", 5000),   # 5,000 H1 bars (~1 year)
        ("D1", 2000),   # 2,000 D1 bars (~8 years)
    ]

    registry = DatasetRegistry(os.path.join(docs_data_dir, "DATASET_MANIFEST.json"))
    vault = ProtectedOOSVault(vault_directory=data_vault_dir)

    for tf, bar_count in resolutions:
        print(f"\n--- Ingesting XAUUSD {tf} (Target: {bar_count} bars) ---", flush=True)
        try:
            df_raw, meta = adapter.fetch_data(symbol="XAUUSD", timeframe=tf, count=bar_count)
            print(f"Successfully fetched {len(df_raw)} bars from {df_raw.index[0]} to {df_raw.index[-1]}", flush=True)
        except Exception as e:
            print(f"Error fetching {tf} data from MT5: {e}", flush=True)
            continue

        # 1. Save cold raw payload
        raw_parquet_path = os.path.join(data_raw_dir, f"xauusd_{tf.lower()}_raw.parquet")
        raw_csv_path = os.path.join(data_raw_dir, f"xauusd_{tf.lower()}_raw.csv")
        df_raw.to_parquet(raw_parquet_path, compression="snappy")
        df_raw.to_csv(raw_csv_path)
        print(f"Raw payload cold-archived to: {raw_parquet_path}")

        # 2. Run Comprehensive Stage 3 Quality Audit
        dataset_version = "v1.0.0"
        dataset_id = f"QROS-DATA-XAUUSD-{tf.upper()}-{dataset_version}"
        quality_report = audit_dataset_quality(
            df=df_raw,
            symbol="XAUUSD",
            timeframe=tf,
            dataset_version=dataset_version,
        )
        print(f"Quality Audit Outcome: {quality_report.overall_approval_status}")
        print(f"Dataset SHA-256: {quality_report.dataset_sha256}")

        # Save Quality Report Markdown
        report_md_path = os.path.join(docs_data_dir, f"XAUUSD_{tf.upper()}_DATA_QUALITY_REPORT.md")
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(quality_report.generate_markdown())
        print(f"Quality report saved to: {report_md_path}")

        # 3. Perform 4-Tier Chronological Partitioning (20% EDA, 40% Train, 20% Val, 20% OOS)
        splitter = DataSplitter(eda_pct=0.20, train_pct=0.40, val_pct=0.20, oos_pct=0.20)
        split_ds = splitter.split(df_raw, lock_oos=False)  # Temporary read for vault storage

        # 4. Vault Protected Tier 4 OOS
        df_oos = split_ds._oos
        vault_file, oos_hash = vault.vault_oos_dataset(
            df_oos=df_oos,
            dataset_id=dataset_id,
            symbol="XAUUSD",
            timeframe=tf,
        )
        print(f"Tier 4 Protected OOS vaulted to: {vault_file} (SHA-256: {oos_hash[:16]}...)")

        # 5. Save Research Partitions (Tiers 1, 2, 3) to processed directory
        eda_path = os.path.join(data_proc_dir, f"xauusd_{tf.lower()}_tier1_eda.parquet")
        train_path = os.path.join(data_proc_dir, f"xauusd_{tf.lower()}_tier2_train.parquet")
        val_path = os.path.join(data_proc_dir, f"xauusd_{tf.lower()}_tier3_val.parquet")
        full_proc_path = os.path.join(data_proc_dir, f"xauusd_{tf.lower()}_full_clean.parquet")

        split_ds.eda.to_parquet(eda_path, compression="snappy")
        split_ds.train.to_parquet(train_path, compression="snappy")
        split_ds.validation.to_parquet(val_path, compression="snappy")
        df_raw.to_parquet(full_proc_path, compression="snappy")

        # 6. Generate Dataset Manifest
        partitions_info = {
            "tier_1_eda": PartitionInfo(
                tier_name="Tier 1: Discovery / EDA",
                bar_count=len(split_ds.eda),
                percentage=0.20,
                start_time_utc=split_ds.eda.index[0].isoformat(),
                end_time_utc=split_ds.eda.index[-1].isoformat(),
                partition_sha256=compute_dataset_hash(split_ds.eda),
                is_vaulted_oos=False,
            ),
            "tier_2_train": PartitionInfo(
                tier_name="Tier 2: In-Sample Training",
                bar_count=len(split_ds.train),
                percentage=0.40,
                start_time_utc=split_ds.train.index[0].isoformat(),
                end_time_utc=split_ds.train.index[-1].isoformat(),
                partition_sha256=compute_dataset_hash(split_ds.train),
                is_vaulted_oos=False,
            ),
            "tier_3_val": PartitionInfo(
                tier_name="Tier 3: Validation / Tuning",
                bar_count=len(split_ds.validation),
                percentage=0.20,
                start_time_utc=split_ds.validation.index[0].isoformat(),
                end_time_utc=split_ds.validation.index[-1].isoformat(),
                partition_sha256=compute_dataset_hash(split_ds.validation),
                is_vaulted_oos=False,
            ),
            "tier_4_oos": PartitionInfo(
                tier_name="Tier 4: Protected Out-of-Sample",
                bar_count=len(df_oos),
                percentage=0.20,
                start_time_utc=df_oos.index[0].isoformat(),
                end_time_utc=df_oos.index[-1].isoformat(),
                partition_sha256=oos_hash,
                is_vaulted_oos=True,
            ),
        }

        manifest = DatasetManifest(
            dataset_id=dataset_id,
            asset="XAUUSD",
            timeframe=tf,
            dataset_version=dataset_version,
            total_bars=len(df_raw),
            calendar_span_years=quality_report.calendar_span_years,
            full_dataset_sha256=quality_report.dataset_sha256,
            partitions=partitions_info,
            source_metadata=meta,
            quality_approval_status=quality_report.overall_approval_status,
        )

        registry.register_dataset(manifest)
        print(f"Manifest registered in DATASET_MANIFEST.json for {dataset_id}")

    # Generate master data quality summary report
    master_report_path = os.path.join(docs_data_dir, "XAUUSD_DATA_QUALITY_REPORT.md")
    # Read M5 quality report for master summary
    m5_rep_path = os.path.join(docs_data_dir, "XAUUSD_M5_DATA_QUALITY_REPORT.md")
    if os.path.exists(m5_rep_path):
        with open(m5_rep_path, "r", encoding="utf-8") as f_src:
            content = f_src.read()
        with open(master_report_path, "w", encoding="utf-8") as f_dst:
            f_dst.write(content)
        print(f"Master quality report written to: {master_report_path}")

    print("\n=== Real Market Data Acquisition & Vaulting Completed Successfully ===")


if __name__ == "__main__":
    main()
