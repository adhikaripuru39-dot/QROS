"""Process settings from environment / .env, and YAML config loaders."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import FirmProfile, InstrumentConfig

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QROS_", env_file=str(PROJECT_DIR / ".env"),
                                      extra="ignore")

    database_url: str = f"sqlite:///{(PROJECT_DIR / 'var' / 'qros.db').as_posix()}"
    # Dashboard API token. MUST be set; API refuses to start with the placeholder in non-dev.
    api_token: SecretStr = SecretStr("change-me")
    env: Literal["dev", "prod"] = "dev"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    stale_after_seconds: int = 15

    # Broker
    broker_adapter: Literal["none", "mt5"] = "none"
    mt5_path: Optional[str] = None
    mt5_login: Optional[int] = None
    mt5_password: Optional[SecretStr] = None
    mt5_server: Optional[str] = None
    executor_interval_seconds: float = 2.0
    # Monitoring uses the terminal session without granting order submission.
    order_execution_enabled: bool = False
    enforce_example_profile_block: bool = True
    halt_action: Literal["block_entries", "flatten_managed"] = "flatten_managed"
    news_calendar_path: Optional[Path] = None
    news_filter_enabled: bool = False
    news_minutes_before: int = Field(default=5,ge=0,le=240)
    news_minutes_after: int = Field(default=5,ge=0,le=240)
    news_min_importance: int = Field(default=2,ge=0,le=3)
    news_max_age_seconds: int = Field(default=120,ge=30,le=180)
    paper_initial_balance: Optional[float] = None
    paper_commission_per_lot_round_turn: Optional[float] = None
    paper_swap_per_lot_day: Optional[float] = None
    paper_slippage_points: float = 5.0
    log_dir: Path = PROJECT_DIR / "var" / "logs"
    # After a crash/VPS restart, a previously RUNNING state resumes as PAUSED_ENTRIES unless true.
    resume_on_restart: bool = False

    # Hard gate #1 for live trading. Only settable on the host, never via API.
    live_trading_enabled: bool = False

    config_dir: Path = CONFIG_DIR
    data_dir: Path = PROJECT_DIR / "var" / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_firm_profiles(config_dir: Path | None = None) -> dict[str, FirmProfile]:
    d = (config_dir or get_settings().config_dir) / "firms"
    out: dict[str, FirmProfile] = {}
    for p in sorted(d.glob("*.yaml")):
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        prof = FirmProfile.model_validate(raw)
        out[prof.id] = prof
    return out


def load_instruments(config_dir: Path | None = None) -> list[InstrumentConfig]:
    p = (config_dir or get_settings().config_dir) / "instruments.yaml"
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return [InstrumentConfig.model_validate(x) for x in raw["instruments"]]


def load_defaults(config_dir: Path | None = None) -> dict:
    p = (config_dir or get_settings().config_dir) / "defaults.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))
