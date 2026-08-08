"""Part 3: Data Engineering — storage tiers, partitioning, dataset metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Tier(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


@dataclass(frozen=True)
class TierSpec:
    """A storage tier per Part 3 ch.1.1."""

    tier: Tier
    technology: str
    latency: str
    retention: str
    storage_media: str
    primary_use: str


TIERS: tuple[TierSpec, ...] = (
    TierSpec(
        tier=Tier.HOT,
        technology="KDB+/q, ClickHouse, In-Memory Shared Memory (Shared Memory IPC)",
        latency="Sub-millisecond (< 1 ms)",
        retention="30 Days, NVMe PCIe Gen5 SSD Storage",
        storage_media="NVMe PCIe Gen5 SSD",
        primary_use="Real-time feature calculation, intraday order book reconstruction, live trading feed",
    ),
    TierSpec(
        tier=Tier.WARM,
        technology="Apache Iceberg / Delta Lake on MinIO / AWS S3, Parquet",
        latency="10 - 100 milliseconds",
        retention="10 Years, High-throughput Object Storage",
        storage_media="High-throughput Object Storage",
        primary_use="Quantitative research backtesting, walk-forward signal validation, feature store",
    ),
    TierSpec(
        tier=Tier.COLD,
        technology="AWS S3 Glacier Flexible Retrieval / Deep Archive",
        latency="1 to 5 hours",
        retention="Indefinite / Permanent Tape & Blob",
        storage_media="Tape & Blob",
        primary_use="Raw exchange PCAP/SBE payloads, disaster recovery, regulatory compliance archives",
    ),
)


@dataclass(frozen=True)
class DatasetMetadata:
    """Metadata contract embedded in every parquet dataset (Part 3 ch.1.3)."""

    git_commit: str
    etl_version: str
    schema_version: str
    ingested_at: str


def to_arrow_metadata(meta: DatasetMetadata) -> dict[str, str]:
    """Serialize the metadata contract dictionary (Arrow metadata stub)."""
    return {
        "git_commit": meta.git_commit,
        "etl_pipeline_version": meta.etl_version,
        "schema_version": meta.schema_version,
        "ingested_at": meta.ingested_at,
    }


def partition_path(
    tier: Tier,
    asset_class: str,
    data_type: str,
    year: int,
    month: int,
    day: int,
    symbol: str,
    root: str = "s3://qros-data-lake",
) -> str:
    """Part 3 ch.1.2 hive-style partition path.

    Standard:
        s3://qros-data-lake/tier=<tier>/asset_class=<ac>/data_type=<dt>/
        year=<y>/month=<m>/day=<d>/<symbol>.parquet
    """
    return (
        f"{root}/tier={tier.value}"
        f"/asset_class={asset_class}"
        f"/data_type={data_type}"
        f"/year={year:04d}/month={month:02d}/day={day:02d}"
        f"/{symbol}.parquet"
    )