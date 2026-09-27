# QROS Standard: Research Search Space & Universe Standard
**Standard ID:** QROS-STD-SPACE-003  
**File:** `03_RESEARCH_SEARCH_SPACE.md`  
**Mission:** QROS-RESEARCH-001  
**Status:** Mandatory Institutional Standard  
**Authority:** QROS Architecture Authority  

---

## 1. Research Universe Architecture

QROS structures its quantitative inquiry across 9 orthogonal dimensions of market reality. Every hypothesis formulated within the platform must be positioned within this coordinate space:

```
                      ┌────────────────────────────────────────┐
                      │      QROS 9-DIMENSIONAL UNIVERSE       │
                      ├────────────────────────────────────────┤
                      │ 1. Asset & Market Dimension            │
                      │ 2. Temporal & Session Dimension        │
                      │ 3. Price Structural Dimension          │
                      │ 4. Volatility Dimension                │
                      │ 5. Momentum & Persistence Dimension    │
                      │ 6. Mean Reversion & Distance Dimension │
                      │ 7. Market Regime Dimension             │
                      │ 8. Microstructure & Liquidity Proxies  │
                      │ 9. Macroeconomic Event Context         │
                      └────────────────────────────────────────┘
```

---

## 2. Specification of Search Dimensions

### 1. Asset & Market Dimension
- **Primary Focus**: `XAUUSD` (Spot Gold vs. US Dollar).
- **Secondary Tier (Major FX)**: `EURUSD`, `GBPUSD`, `USDJPY`, `AUDUSD`, `USDCAD`, `USDCHF`, `NZDUSD`.
- **Secondary Tier (Equity Indices)**: `US500` (S&P 500), `USTEC` (Nasdaq 100), `US30` (Dow Jones), `GER40` (DAX).
- **Asset Classes**: Commodities, Currencies, Index Swaps.

### 2. Temporal & Session Dimension
- **Global Sessions**: 
  - Asian Session: 00:00 – 08:00 UTC (Tokyo/Sydney)
  - European / London Session: 07:00 – 16:00 UTC
  - North American / New York Session: 12:00 – 21:00 UTC
- **Temporal Junctions**:
  - London / New York Overlap: 12:00 – 16:00 UTC
  - London Fixing: 16:00 UTC (11:00 AM EST)
  - Daily Settlement & Rollover: 21:00 – 22:00 UTC
- **Periodicity**: Day-of-week seasonality (Monday open dynamics, Friday positioning unwind), Month-end rebalancing flows.

### 3. Price Structural Dimension
- **Reference Levels**: Previous Day High/Low (PDH/PDL), Session High/Low, Weekly Open/High/Low.
- **Structural Formations**: Range contraction/compression (narrow bar regimes), expansion/displacement bars, fair value gaps / price imbalances, liquidity pool sweeps.
- **Swing Topology**: Fractal swing highs/lows, higher-high/lower-low structural breaks.

### 4. Volatility Dimension
- **Metrics**: Average True Range (ATR), Realized Historical Volatility ($\sigma_{\text{realized}}$), Garman-Klass volatility, Parkinson volatility.
- **Regimes**: Volatility compression ($\text{ATR}_{14} < \text{Quantile}_{20}$), Volatility shock ($\text{ATR}_5 > 2.5 \times \text{ATR}_{50}$).

### 5. Momentum & Directional Persistence Dimension
- **Characteristics**: Autocorrelation of returns ($\rho(k)$), Hurst Exponent ($H > 0.55$), directional drift following range breakouts, order flow momentum continuation.
- **Exhaustion**: Multi-bar deceleration at standard deviation boundary bands.

### 6. Mean Reversion & Statistical Distance Dimension
- **Metrics**: Normalized distance from rolling anchor ($Z = \frac{P_t - \mu}{\sigma}$), Ornstein-Uhlenbeck mean-reversion speed ($\theta$), Half-life ($\tau = \frac{\ln 2}{\theta}$).
- **Boundaries**: Deviation extremes ($|Z| > 2.5$), structural channel boundaries.

### 7. Market Regime Dimension
- **Classification Grid**:
  - Trend-Dominant (Bullish / Bearish)
  - Range-Bound / Mean-Reverting (Low Volatility)
  - Range-Bound (High Volatility Choppy)
  - Regime Transition (High-to-Low Volatility, Range-to-Trend Breakout)

### 8. Microstructure & Liquidity Proxies
- **Friction & Depth Indicators**: Bid-Ask Spread distribution across session transitions, Tick Volume spikes around structural levels, slippage models, market depth proxies.

### 9. Macroeconomic Event Context
- **Scheduled Economic Catalysts**: US CPI, Non-Farm Payrolls (NFP), FOMC Interest Rate Decisions, ECB/BOE Decisions.
- **Event Windows**: Pre-announcement volatility freeze ($T - 30\text{m}$), announcement volatility spike ($T \pm 5\text{m}$), post-announcement drift ($T + 15\text{m} \dots T + 120\text{m}$).

---

## 3. Strict Anti-Indicator-Driven Mandate

> [!CAUTION]
> **CRITICAL RULE**: QROS research shall **NEVER** degenerate into ungrounded technical indicator curve-fitting.

### Prohibited Research Activities:
1. **Combinatorial Indicator Brute-Forcing**:
   - Sweeping RSI(14 vs 21), MACD(12,26,9 vs 10,20,5), Bollinger Band standard deviations, or Moving Average crossovers to identify the "highest backtest profit."
2. **Indicator-as-Mechanism Fallacy**:
   - Claiming an edge exists because "RSI dropped below 30." RSI is a mathematical derivative of closing prices, not a market participant with economic agency.
3. **Data Snooping via Indicator Grids**:
   - Testing 10,000 parameter combinations and reporting the single profitable run without Deflated Sharpe Ratio penalty adjustments.

### Permitted Use of Technical Indicators:
- Indicators are allowed **only as secondary feature representations or measurement tools** of an already defined, economically grounded hypothesis (e.g., using ATR strictly to measure whether a defined behavioral news-drift hypothesis operates differently under high vs. low volatility regimes).
