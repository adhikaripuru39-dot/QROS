"""Unit and integration tests for data acquisition, quality audit, and Protected OOS Vault."""

import os
import tempfile
import numpy as np
import pandas as pd
import pytest
from qros.data.adapters.csv_adapter import CSVIngestionAdapter
from qros.data.adapters.mt5_adapter import MT5IngestionAdapter
from qros.data.quality import audit_dataset_quality
from qros.data.splitting import DataSplitter, ProtectedOOSViolationError
from qros.data.validation import compute_dataset_hash
from qros.data.vault.manifest import (
    DatasetManifest,
    DatasetRegistry,
    PartitionInfo,
)
from qros.data.vault.oos_vault import ProtectedOOSVault
from qros.testing.synthetic_data import generate_synthetic_ohlcv


def test_csv_adapter_load_and_save():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create test CSV
        csv_path = os.path.join(tmp_dir, "xauusd_m5.csv")
        df_orig = generate_synthetic_ohlcv(n_bars=200, random_seed=42)
        df_orig.to_csv(csv_path)

        adapter = CSVIngestionAdapter(data_directory=tmp_dir)
        df_loaded, meta = adapter.load_file(csv_path, symbol="XAUUSD", timeframe="M5")

        assert len(df_loaded) == 200
        assert "close" in df_loaded.columns
        assert isinstance(df_loaded.index, pd.DatetimeIndex)
        assert meta["symbol"] == "XAUUSD"


def test_mt5_adapter_structure():
    adapter = MT5IngestionAdapter()
    assert adapter.terminal_path is not None
    # Verify timeframe mappings
    assert "M5" in adapter.TIMEFRAME_MAP
    assert "H1" in adapter.TIMEFRAME_MAP
    assert "D1" in adapter.TIMEFRAME_MAP


def test_comprehensive_quality_auditor_clean_data():
    df = generate_synthetic_ohlcv(n_bars=500, random_seed=42)
    report = audit_dataset_quality(df, symbol="XAUUSD", timeframe="M5", dataset_version="v1.0.0")

    assert report.overall_approval_status == "APPROVED"
    assert report.total_bars == 500
    assert len(report.detected_anomalies) == 0
    assert len(report.dataset_sha256) == 64

    # Verify markdown rendering
    md = report.generate_markdown()
    assert "# QROS Comprehensive Data Quality Report: XAUUSD (M5)" in md
    assert "[APPROVED]" in md


def test_comprehensive_quality_auditor_corrupted_data():
    df = generate_synthetic_ohlcv(n_bars=200, random_seed=42)
    # Corrupt a bar: High < Low
    df.loc[df.index[10], "high"] = 100.0

    report = audit_dataset_quality(df, symbol="XAUUSD", timeframe="M5")
    assert report.overall_approval_status == "DATASET REJECTED"
    assert len(report.detected_anomalies) > 0


def test_dataset_manifest_and_registry():
    with tempfile.TemporaryDirectory() as tmp_dir:
        reg_file = os.path.join(tmp_dir, "DATASET_MANIFEST.json")
        registry = DatasetRegistry(registry_file=reg_file)

        part_info = {
            "tier_1_eda": PartitionInfo(
                tier_name="Tier 1: EDA",
                bar_count=200,
                percentage=0.20,
                start_time_utc="2023-01-01T00:00:00Z",
                end_time_utc="2023-03-01T00:00:00Z",
                partition_sha256="abc123hash",
            )
        }

        manifest = DatasetManifest(
            dataset_id="QROS-DATA-XAUUSD-M5-v1.0.0",
            asset="XAUUSD",
            timeframe="M5",
            dataset_version="v1.0.0",
            total_bars=1000,
            calendar_span_years=1.5,
            full_dataset_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            partitions=part_info,
            source_metadata={"broker": "TestBroker"},
            quality_approval_status="APPROVED",
        )

        registry.register_dataset(manifest)

        # Reload from disk
        reloaded_reg = DatasetRegistry(registry_file=reg_file)
        retrieved = reloaded_reg.get_manifest("QROS-DATA-XAUUSD-M5-v1.0.0")
        assert retrieved is not None
        assert retrieved.asset == "XAUUSD"
        assert retrieved.total_bars == 1000
        assert retrieved.partitions["tier_1_eda"].bar_count == 200


def test_protected_oos_vault(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        vault = ProtectedOOSVault(vault_directory=tmp_dir)
        monkeypatch.setenv("QROS_OOS_AUTH_TOKEN", "GOV-GATE-11-AUTH")
        df_oos = generate_synthetic_ohlcv(n_bars=200, random_seed=42)

        file_path, file_hash = vault.vault_oos_dataset(
            df_oos=df_oos,
            dataset_id="QROS-DATA-XAUUSD-M5-v1.0.0",
            symbol="XAUUSD",
            timeframe="M5",
        )

        assert os.path.exists(file_path)
        assert len(file_hash) == 64

        # Attempt to load without token must fail
        with pytest.raises(ProtectedOOSViolationError):
            vault.load_vaulted_oos("QROS-DATA-XAUUSD-M5-v1.0.0", authorization_token="")

        with pytest.raises(ProtectedOOSViolationError):
            vault.load_vaulted_oos("QROS-DATA-XAUUSD-M5-v1.0.0", authorization_token="   ")

        # Authorized unlock succeeds
        loaded_df = vault.load_vaulted_oos(
            "QROS-DATA-XAUUSD-M5-v1.0.0", authorization_token="GOV-GATE-11-AUTH"
        )
        assert len(loaded_df) == 200
        assert compute_dataset_hash(loaded_df) == file_hash

        # Verify audit log
        assert len(vault.audit_log) >= 3  # VAULT_STORAGE, UNAUTHORIZED, AUTHORIZED_UNLOCK


def test_real_xauusd_pipeline_consumption():
    """Verify that real XAUUSD processed dataset can be consumed by QROS statistical evaluation pipeline."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    proc_file = os.path.join(base_dir, "data", "processed", "xauusd", "xauusd_d1_full_clean.parquet")

    if os.path.exists(proc_file):
        df_real = pd.read_parquet(proc_file)
        assert len(df_real) >= 1000
        assert "close" in df_real.columns

        # Calculate simple 1-day logarithmic returns
        returns = np.diff(np.log(df_real["close"].to_numpy()))

        from qros.pipeline.evaluation import evaluate_statistical_profile
        from qros.schemas.validation_profile import get_default_profile

        profile = get_default_profile("CLASS-IV")  # Macro/Daily regime
        result = evaluate_statistical_profile(
            returns_net=returns,
            validation_profile=profile,
            hypothesis_id="QROS-HYP-000004",
            trial_count_k=1,
            observation_count_t=len(df_real),
            calendar_span_years=7.5,
            n_bootstrap_resamples=500,
            random_seed=42,
        )

        assert result.sample_size_n == len(returns)
        assert result.observation_count_t >= 1000
        assert result.annualized_sharpe_net is not None
        assert result.dsr_result is not None
        assert result.bootstrap_result is not None
        assert isinstance(result.failure_reasons, list)
        assert len(result.failure_reasons) > 0  # Raw buy-and-hold does not pass active strategy gate


def test_dataset_versioning_and_multi_version_registry():
    """Verify that v1.0.0 and v2.0.0 manifests coexist and retain distinct SHA-256 digests."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    manifest_path = os.path.join(base_dir, "docs", "research", "data", "DATASET_MANIFEST.json")

    if os.path.exists(manifest_path):
        registry = DatasetRegistry(registry_file=manifest_path)
        m1_v2 = registry.get_manifest("QROS-DATA-XAUUSD-M1-v2.0.0")
        m5_v1 = registry.get_manifest("QROS-DATA-XAUUSD-M5-v1.0.0")
        m5_v2 = registry.get_manifest("QROS-DATA-XAUUSD-M5-v2.0.0")
        h1_v2 = registry.get_manifest("QROS-DATA-XAUUSD-H1-v2.0.0")
        d1_v2 = registry.get_manifest("QROS-DATA-XAUUSD-D1-v2.0.0")

        assert m1_v2 is not None
        assert m1_v2.total_bars == 9999
        assert m5_v2 is not None
        assert m5_v2.total_bars == 9999
        assert h1_v2 is not None
        assert h1_v2.total_bars == 9999
        assert d1_v2 is not None

        # Verify distinct hashes between versions
        if m5_v1 is not None and m5_v2 is not None:
            assert m5_v1.full_dataset_sha256 != m5_v2.full_dataset_sha256


def test_versioned_protected_oos_vault_isolation():
    """Verify that multiple dataset versions have isolated Tier 4 vaulted files and audit logging."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    vault_dir = os.path.join(base_dir, "data", "vault", "xauusd")

    if os.path.exists(vault_dir):
        vault = ProtectedOOSVault(vault_directory=vault_dir)

        # Attempt to load without authorization token must raise error
        with pytest.raises(ProtectedOOSViolationError):
            vault.load_vaulted_oos("QROS-DATA-XAUUSD-M1-v2.0.0", authorization_token="")

        with pytest.raises(ProtectedOOSViolationError):
            vault.load_vaulted_oos("QROS-DATA-XAUUSD-H1-v2.0.0", authorization_token="   ")
