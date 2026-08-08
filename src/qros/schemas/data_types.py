"""Part 1 ch.2: Comprehensive Financial Market Data Taxonomy — 13 data types.

Each entry transcribes the handbook row: why it matters, source, advantages,
disadvantages, biases, cleaning requirements, storage, research usefulness.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialDataType:
    """A financial market data category in the QROS taxonomy."""

    id: str
    title: str
    cleaning_rules: tuple[str, ...]
    storage: str
    biases: tuple[str, ...]
    research_use: str


DATA_TYPE_CATALOG: tuple[FinancialDataType, ...] = (
    FinancialDataType(
        id="OHLC_BARS",
        title="OHLC Bar Data (Time, Volume, Tick & Dollar Bars)",
        cleaning_rules=(
            "Enforce High >= max(Open, Close) and Low <= min(Open, Close)",
            "Reject zero-volume bars unless explicitly flagged as static quote fills",
        ),
        storage="Parquet format partitioned by Asset_Class/Symbol/Year/Month",
        biases=("Session close misalignment", "Bar construction timing bugs"),
        research_use="Volatility estimators (Garman-Klass, Yang-Zhang), momentum features, multi-day trend hypotheses",
    ),
    FinancialDataType(
        id="TICK_MICROSTRUCTURE",
        title="Tick Data & Market Microstructure (Trade Tape, Time & Sales)",
        cleaning_rules=(
            "Filter out Form-T, late prints, derivative hedges, odd-lot non-consolidated flags",
        ),
        storage="High-compression columnar storage (ZSTD level 7 Parquet or KDB+ splay databases)",
        biases=("Out-of-order packet arrival", "Exchange re-transmissions", "Non-firm trade reports"),
        research_use="Trade aggressor classification (Lee-Ready, Bulk Volume Classification), market impact modeling, flow toxicity (VPIN)",
    ),
    FinancialDataType(
        id="ORDER_BOOK",
        title="Depth of Market & Order Book Data (Level I, Level II, Level III)",
        cleaning_rules=(
            "Deduplicate sequence numbers",
            "Validate price level sorting (bids strictly descending, asks strictly ascending)",
        ),
        storage="Raw pcap format for cold storage; compressed LOB snapshot state tables for hot storage",
        biases=("Message cancellation latency masking true available liquidity", "Spoofing", "Phantom liquidity"),
        research_use="Microstructure alpha features, order flow imbalance, market maker inventory modeling",
    ),
    FinancialDataType(
        id="ECONOMIC_CALENDAR",
        title="Economic Calendar, Central Bank Events & Macro Data",
        cleaning_rules=(
            "Dual-timestamping (Observation Period, Initial Release Time, Revision Release Time, Revised Value)",
        ),
        storage="Relational point-in-time SQL database with strict bitemporal indexing",
        biases=("Revision bias", "Look-ahead bias from revised macro series used without point-in-time tracking"),
        research_use="Event-driven volatility modeling, macroeconomic regime classification, yield curve positioning",
    ),
    FinancialDataType(
        id="OPTIONS",
        title="Options Data (Implied Volatility, Open Interest, Greeks)",
        cleaning_rules=(
            "Filter out zero-bid options",
            "Filter non-tradable wide-spread contracts",
            "Filter arbitrage-violating option prices",
        ),
        storage="Multi-dimensional arrays / Parquet tables keyed by Underlying/Expiry/Strike/OptionType",
        biases=("Stale settlement prices on illiquid contracts",),
        research_use="Implied volatility skew/smile features, Gamma Exposure (GEX) pinning models, Vanna/Charm flows",
    ),
    FinancialDataType(
        id="SENTIMENT_NEWS",
        title="Sentiment & News Data",
        cleaning_rules=(
            "Store raw textual payload alongside score versioning",
            "Strictly enforce timestamp of headline publication",
        ),
        storage="Document store (Elasticsearch / MongoDB) and Parquet tables for numerical sentiment scores",
        biases=("Vendor reprocessing bias (retroactive historical sentiment rescoring)",),
        research_use="Post-earnings announcement drift (PEAD), crisis shock response, topic modeling features",
    ),
    FinancialDataType(
        id="ALTERNATIVE",
        title="Alternative Data (Satellite, Web Traffic, Supply Chain)",
        cleaning_rules=(
            "Normalize panels for panel turnover",
            "Map entity tickers to point-in-time PERMNO/FIGI IDs",
        ),
        storage="Cloud data lake with S3/GCS parquet files",
        biases=("Panel restructuring bias", "Survivor bias in mapped entity universes"),
        research_use="Fundamental revenue forecasting, foot-traffic sentiment, supply chain bottleneck detection",
    ),
    FinancialDataType(
        id="CROSS_ASSET_INTERMARKET",
        title="Cross-Asset & Intermarket Data (Commodities, FX, Rates, ETFs)",
        cleaning_rules=(
            "Align timestamps to UTC nanoseconds",
            "Apply forward-fill rules for non-overlapping exchange sessions",
        ),
        storage="Multi-asset standardized Parquet tables",
        biases=("Improper timezone conversion masking true market order flow lead times",),
        research_use="Intermarket momentum, cross-asset spillover models, flight-to-quality indicators",
    ),
    FinancialDataType(
        id="LIQUIDITY_FUNDING",
        title="Liquidity & Funding Data (Funding Rates, Repo, Dark Pool Flows)",
        cleaning_rules=("Validate rate quotes against central bank corridor bounds",),
        storage="Time series database tables",
        biases=("Delayed dark pool reporting (ATS regulatory lag)",),
        research_use="Liquidity crisis forecasting, funding arbitrage, perpetual swap premium models",
    ),
    FinancialDataType(
        id="VOLATILITY_INDEXES",
        title="Volatility Indexes (VIX, MOVE, VVIX, SKEW)",
        cleaning_rules=("Filter out index calculation glitches during market open auction turbulence",),
        storage="Standardized daily and intraday time series tables",
        biases=("Intraday calculation spikes due to illiquid OTM option quotes",),
        research_use="Volatility regime switching models, variance risk premium harvest strategies",
    ),
    FinancialDataType(
        id="CORRELATION_MATRICES",
        title="Correlation Assets & Dynamic Covariance Matrices",
        cleaning_rules=(
            "Apply Random Matrix Theory (RMT) denoising",
            "Apply shrinkage estimators (Ledoit-Wolf)",
        ),
        storage="Binary matrix storage (HDF5 / Zarr arrays)",
        biases=("Epps effect (correlation breakdown at ultra-high frequencies due to asynchronous sampling)",),
        research_use="Pair trading, eigen-portfolio decomposition, risk-parity allocation",
    ),
    FinancialDataType(
        id="MACRO_YIELD_CURVES",
        title="Macro Indicators & Global Yield Curves",
        cleaning_rules=("Store raw benchmark yields alongside spline parameterizations",),
        storage="Relational time series tables",
        biases=("Interpolation model bias (Nelson-Siegel vs Cubic Spline curve fitting differences)",),
        research_use="Duration risk modeling, macro factor risk attribution",
    ),
    FinancialDataType(
        id="COT_POSITIONING",
        title="Commitment of Traders (COT) & Exchange Positioning Reports",
        cleaning_rules=("Set Available_Timestamp strictly to Friday 15:30 EST post-release",),
        storage="Relational tables",
        biases=("Publication lag bias if Friday release date is assigned back to Tuesday observation date",),
        research_use="Long-term trend reversal models, institutional extreme sentiment indicators",
    ),
)

DATA_TYPE_IDS: frozenset[str] = frozenset(dt.id for dt in DATA_TYPE_CATALOG)


def validate_data_type_id(value: str) -> None:
    """Raise ValueError if ``value`` is not one of the 13 handbook data types."""
    if value not in DATA_TYPE_IDS:
        raise ValueError(
            f"Unknown data type {value!r}. Valid: {sorted(DATA_TYPE_IDS)}"
        )


@dataclass(frozen=True)
class DepthSpec:
    """Order book depth level per Part 1 ch.2.3 (Level I, II, III)."""

    level: str
    fields: tuple[str, ...]
    research_application: str


DEPTH_LEVELS: tuple[DepthSpec, ...] = (
    DepthSpec(
        level="L1",
        fields=("Best Bid Price/Size", "Best Ask Price/Size", "Timestamp"),
        research_application="Spread analysis, quote mid-price returns, execution cost benchmarking.",
    ),
    DepthSpec(
        level="L2",
        fields=("Top 10-50 price levels with aggregate volume and order count",),
        research_application="Order book imbalance (OBI), market depth liquidity, queue positioning.",
    ),
    DepthSpec(
        level="L3",
        fields=("Individual order IDs: Add, Cancel, Modify, Execute events",),
        research_application="Queue priority tracking, institutional order detection, latency arbitrage.",
    ),
)