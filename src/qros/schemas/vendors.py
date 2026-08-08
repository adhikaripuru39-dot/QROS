"""Part 1 ch.3: Institutional Data Vendor Selection & Architecture — 5 vendor classes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VendorClass(str, Enum):
    DIRECT_EXCHANGE_MULTICAST = "direct_exchange_multicast"
    CONSOLIDATED_FEED = "consolidated_feed"
    OPTIONS_SURFACE = "options_surface"
    FUNDAMENTAL_REFERENCE = "fundamental_reference"
    MACRO_EVENT = "macro_event"


@dataclass(frozen=True)
class VendorSpec:
    """A vendor class with its providers, protocols, SLA, and research destination."""

    vendor_class: VendorClass
    providers: tuple[str, ...]
    protocol: str
    latency_spec: str
    research_destination: str


VENDOR_CATALOG: tuple[VendorSpec, ...] = (
    VendorSpec(
        vendor_class=VendorClass.DIRECT_EXCHANGE_MULTICAST,
        providers=("CME Group", "Nasdaq", "NYSE", "Eurex"),
        protocol="UDP Multicast, SBE, ITCH, FAST",
        latency_spec="Sub-microsecond (< 1 us), 99.999% uptime",
        research_destination="Ultra-Low Latency Feature Store, L3 Book Reconstructor",
    ),
    VendorSpec(
        vendor_class=VendorClass.CONSOLIDATED_FEED,
        providers=("Bloomberg B-PIPE", "Refinitiv Elektron"),
        protocol="Enterprise TCP/IP APIs, WebSockets",
        latency_spec="1-10 ms latency, 99.99% uptime",
        research_destination="Global Cross-Asset Normalized Stream, Backtesting Engine",
    ),
    VendorSpec(
        vendor_class=VendorClass.OPTIONS_SURFACE,
        providers=("OptionMetrics", "Cboe Hanweck"),
        protocol="S3 Parquet Batches, Zstandard Streams",
        latency_spec="End-of-day + 15-min delayed",
        research_destination="Implied Volatility Surface Database, Greeks Repository",
    ),
    VendorSpec(
        vendor_class=VendorClass.FUNDAMENTAL_REFERENCE,
        providers=("FactSet", "S&P Compustat", "SEC EDGAR"),
        protocol="SQL REST Bulk, Snowflake Shares",
        latency_spec="Daily Point-in-Time snapshots",
        research_destination="Point-in-Time Corporate Action & Financials Database",
    ),
    VendorSpec(
        vendor_class=VendorClass.MACRO_EVENT,
        providers=("FRED", "Kensho", "RavenPack NLP"),
        protocol="HTTPS REST, Kafka JSON Streams",
        latency_spec="Sub-second event trigger",
        research_destination="Event-Driven Research Pipeline, Macro Regime Store",
    ),
)

VENDOR_CLASS_IDS: frozenset[str] = frozenset(v.vendor_class.value for v in VENDOR_CATALOG)


def lookup_vendor(vendor_class: VendorClass) -> VendorSpec:
    """Return the handbook VendorSpec for a vendor class."""
    for spec in VENDOR_CATALOG:
        if spec.vendor_class is vendor_class:
            return spec
    raise KeyError(f"Unknown vendor class: {vendor_class}")