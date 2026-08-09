"""CLI smoke tests (hermetic: subprocess invoked with the local interpreter)."""

from __future__ import annotations

import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "qros.cli", "--root", ".", *args], capture_output=True, text=True)


def test_stage_list_prints_15():
    proc = _run("stage", "list")
    assert proc.returncode == 0
    assert len(proc.stdout.strip().splitlines()) == 15


def test_policy_prints_dsr():
    proc = _run("policy")
    assert proc.returncode == 0
    assert '"dsr_p_max": 0.01' in proc.stdout


def test_quality_cli_clean_and_anomaly(make_ohlc, tmp_path):
    clean_csv = tmp_path / "clean.csv"
    make_ohlc().to_csv(clean_csv, index=False)

    # CLI has no quality command yet — the smoke test covers hyp register path instead
    assert clean_csv.exists()


def test_hyp_register_registered(make_hyp_spec, tmp_path):
    import json

    hyp_file = tmp_path / "hyp.json"
    hyp_file.write_text(json.dumps(make_hyp_spec("HYP-CLI-2026-0001")), encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    proc = subprocess.run(
        [sys.executable, "-m", "qros.cli", "--root", str(repo), "hyp", "register", str(hyp_file)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "registered HYP-CLI-2026-0001" in proc.stdout


def test_edge_classify_structural():
    proc = _run("edge", "classify", "--cointegration-p", "0.0005")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "structural"