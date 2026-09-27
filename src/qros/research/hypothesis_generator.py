"""Hypothesis Generator and Pre-Registration Manager enforcing QROS-STD-HYP-002."""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import yaml
from qros.schemas.hypothesis import HypothesisRecord
from qros.schemas.validation_profile import get_default_profile


def generate_preregistered_hypotheses() -> List[HypothesisRecord]:
    """Construct the initial set of scientifically grounded, falsifiable HypothesisRecords."""

    hypotheses = []

    # 1. QROS-HYP-000001: London Open Breakout & Diurnal Momentum Expansion (Class II)
    hyp1 = HypothesisRecord(
        hypothesis_id="QROS-HYP-000001",
        title="London Open Initial Balance Expansion and Intraday Momentum",
        author="QROS Quantitative Research Team",
        date_created=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        market="COMMODITIES",
        asset="XAUUSD",
        timeframe="M5",
        research_class="CLASS-II",
        market_condition="London Open Session (07:00-11:00 UTC) with Asian Range Compression",
        observation="Stylized Fact QROS-OBS-009 & QROS-OBS-010: Gold trading volume surges by 2.4x at London open (07:00 UTC), and the first 60-minute Initial Balance range is extended in 74% of sessions.",
        hypothesis_statement="Breakouts beyond the Asian session range (00:00-06:59 UTC high/low) occurring during the London opening window (07:00-09:00 UTC) with above-average volume exhibit positive directional momentum over a 60-180 minute holding horizon.",
        plausible_rationale="Physical bullion fixing and European institutional order flow concentration trigger multi-hour directional liquidity drives, creating intraday momentum that persists until early New York overlap.",
        entry_condition="Close of M5 bar crosses above Asian Session High (or below Asian Session Low) between 07:00 and 09:00 UTC, accompanied by M5 tick_volume > 1.5x 20-period moving average.",
        exit_condition="Fixed time exit at 11:00 UTC (pre-NY), or trailing volatility stop at 1.5x ATR(14), or opposite session boundary touch.",
        holding_period="12 to 36 M5 bars (1.0 to 3.0 hours)",
        expected_effect="Net annualized Sharpe >= 1.40, Profit Factor >= 1.40 under Class II 2.5x slippage stress and 200ms latency.",
        null_hypothesis="H_0: Mean net return of London open breakout trades is <= 0.0 (or annualized Sharpe <= 0.0).",
        alternative_hypothesis="H_1: Mean net return of London open breakout trades is strictly > 0.0 with DSR score >= 0.95 at alpha = 0.05.",
        required_data="XAUUSD M5 historical OHLCV with UTC timestamps and tick volume (minimum 400 trade events).",
        potential_confounders="High-impact UK/European macroeconomic news releases (e.g. BOE rate decisions) causing transient spread spikes and false breakouts.",
        transaction_cost_assumptions="Class II Profile: 25 pts nominal spread, 2.5x slippage multiplier, 200ms execution latency buffer.",
        research_status="PRE_REGISTERED",
        validation_profile=get_default_profile("CLASS-II"),
    )
    hypotheses.append(hyp1)

    # 2. QROS-HYP-000002: Volatility Compression -> Multi-Hour Expansion Follow-Through (Class III)
    hyp2 = HypothesisRecord(
        hypothesis_id="QROS-HYP-000002",
        title="Multi-Hour Range Compression Breakout and Volatility Regime Transition",
        author="QROS Quantitative Research Team",
        date_created=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        market="COMMODITIES",
        asset="XAUUSD",
        timeframe="H1",
        research_class="CLASS-III",
        market_condition="Consolidation regime where ATR(6) / ATR(24) < 0.60 across active market sessions",
        observation="Stylized Fact QROS-OBS-002, QROS-OBS-003, & QROS-OBS-007: Realized volatility exhibits autoregressive clustering; periods of extreme range compression (ATR6/ATR24 < 0.60) precede persistent volatility expansion regimes.",
        hypothesis_statement="Directional breakouts from a multi-hour volatility compression state (ATR6/ATR24 < 0.60) on H1 persist in the direction of the breakout over an 8 to 24 hour holding window.",
        plausible_rationale="Consolidation traps resting stop liquidity on both sides of the market. Once directional momentum breaches the range boundary, cascading stop execution and trend-following inflows fuel multi-hour expansion.",
        entry_condition="H1 close breaks above the 24-hour high (or below 24-hour low) following at least 6 consecutive hours of ATR(6)/ATR(24) < 0.60 compression.",
        exit_condition="Exit after 16 H1 bars (16 hours), or upon trailing stop loss of 2.0x ATR(24), or when Garman-Klass volatility reaches 95th percentile.",
        holding_period="8 to 24 H1 bars (8 to 24 hours)",
        expected_effect="Net annualized Sharpe >= 1.20, Profit Factor >= 1.30 under Class III 2.0x slippage stress.",
        null_hypothesis="H_0: Post-compression breakout returns do not differ from zero (E[R_net] <= 0).",
        alternative_hypothesis="H_1: Post-compression breakout returns are strictly positive (E[R_net] > 0) with DSR >= 0.95 under multiple-testing accounting.",
        required_data="XAUUSD H1 historical OHLCV covering at least 1.0 year of continuous non-OOS history (N >= 150 events).",
        potential_confounders="Whipsaw ranges during Federal Reserve FOMC blackout periods or holiday liquidity droughts.",
        transaction_cost_assumptions="Class III Profile: 20 pts nominal spread, 2.0x slippage multiplier, 0ms latency buffer.",
        research_status="PRE_REGISTERED",
        validation_profile=get_default_profile("CLASS-III"),
    )
    hypotheses.append(hyp2)

    # 3. QROS-HYP-000003: Daily Mean Reversion Post-Extreme Tail Expansion (Class IV / Exploratory)
    hyp3 = HypothesisRecord(
        hypothesis_id="QROS-HYP-000003",
        title="Macro Mean Reversion Following 3-Sigma Daily Return Extensions",
        author="QROS Quantitative Research Team",
        date_created=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        market="COMMODITIES",
        asset="XAUUSD",
        timeframe="D1",
        research_class="CLASS-IV",
        market_condition="Macro trend extension where Daily Close deviates > 3.0 standard deviations from 50-day moving average",
        observation="Stylized Fact QROS-OBS-001, QROS-OBS-006, & QROS-OBS-014: Gold return distributions exhibit severe kurtosis (8.91) and Ornstein-Uhlenbeck mean-reversion forces when price stretches to extreme standard deviations.",
        hypothesis_statement="Daily closes exceeding 3.0 rolling standard deviations from the 50-day moving average exhibit statistical mean-reversion drift back toward the 20-day mean over a 3 to 10 day horizon.",
        plausible_rationale="Overextended price moves exhaust aggressive speculative buying/selling power, prompting institutional profit-taking and inventory rebalancing by bullion market makers.",
        entry_condition="Daily close > MA(50) + 3.0 * Std(50) for short mean-reversion, or Daily close < MA(50) - 3.0 * Std(50) for long mean-reversion.",
        exit_condition="Daily close crosses back across the 20-day moving average, or time stop at 10 trading days, or stop loss at 1.5x entry ATR.",
        holding_period="3 to 10 D1 bars (3 to 10 trading days)",
        expected_effect="Net annualized Sharpe >= 1.00, Profit Factor >= 1.25 under Class IV macro hurdles.",
        null_hypothesis="H_0: Mean return of extreme deviation trades is <= 0.0.",
        alternative_hypothesis="H_1: Mean return of extreme deviation trades is strictly > 0.0 with DSR >= 0.95.",
        required_data="XAUUSD D1 historical dataset (N >= 40 events over multiple macro cycles). Note: Available D1 history is currently exploratory.",
        potential_confounders="Structural regime breaks, sudden geopolitical war escalations, or sovereign debt crises triggering runaway multi-week parabolic trends.",
        transaction_cost_assumptions="Class IV Profile: 20 pts spread, 1.5x slippage multiplier, 0ms latency buffer.",
        research_status="PRE_REGISTERED",
        validation_profile=get_default_profile("CLASS-IV"),
    )
    hypotheses.append(hyp3)

    return hypotheses


def generate_expanded_hypotheses_r008() -> List[HypothesisRecord]:
    """Construct scientifically grounded candidate hypotheses for Mission QROS-RESEARCH-008."""

    hypotheses = []

    # 4. QROS-HYP-000004: Daily Macro 50-Day High Breakout Momentum Continuation (Class IV)
    hyp4 = HypothesisRecord(
        hypothesis_id="QROS-HYP-000004",
        title="Daily Macro 50-Day High Breakout Momentum Continuation",
        author="QROS Quantitative Research Team",
        date_created=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        market="COMMODITIES",
        asset="XAUUSD",
        timeframe="D1",
        research_class="CLASS-IV",
        market_condition="Macro trend expansion regime where Daily Close exceeds the prior 50-day highest high",
        observation="Stylized Fact QROS-OBS-019 & Pattern QROS-PAT-001: Gold 5-day forward log return averages +0.72% following a 50-day high breakout across 14 years of macro data (N=186, p < 0.001).",
        hypothesis_statement="Daily closes exceeding the prior 50-day highest high in Gold initiate multi-day upward momentum continuation with positive expected return over a 5 to 20 trading day holding period.",
        plausible_rationale="Gold is a non-yielding monetary reserve asset. Long-term technical breakouts attract institutional asset allocation, central bank accumulation, and CTA momentum chasing that persist over multi-week horizons.",
        entry_condition="Daily Close > Prior 50-Day Highest High (shifted by 1 for point-in-time) with 50-Day MA slope > 0.",
        exit_condition="Exit after 15 D1 bars (15 trading days), or trailing stop loss of 2.0x ATR(20), or when daily close crosses below 20-day moving average.",
        holding_period="5 to 20 D1 bars (5 to 20 trading days)",
        expected_effect="Net annualized Sharpe >= 1.00, Profit Factor >= 1.30 under Class IV macro hurdles.",
        null_hypothesis="H_0: Mean forward return of 50-day high breakout trades is <= 0.0.",
        alternative_hypothesis="H_1: Mean forward return of 50-day high breakout trades is strictly > 0.0 with DSR >= 0.90 under multiple testing accounting.",
        required_data="XAUUSD D1 historical dataset (N >= 40 events over multiple macro cycles). Satisfied by 14-year v3.0.0 D1 dataset.",
        potential_confounders="Central bank surprise interest rate hikes or abrupt dollar liquidity squeezes triggering false breakouts.",
        transaction_cost_assumptions="Class IV Profile: 20 pts spread, 1.5x slippage multiplier, 0ms latency buffer.",
        research_status="PRE_REGISTERED",
        validation_profile=get_default_profile("CLASS-IV"),
    )
    hypotheses.append(hyp4)

    # 5. QROS-HYP-000005: Daily NR4 Range Compression to Multi-Day Volatility Expansion (Class IV)
    hyp5 = HypothesisRecord(
        hypothesis_id="QROS-HYP-000005",
        title="Daily NR4 Range Compression to Multi-Day Volatility Expansion",
        author="QROS Quantitative Research Team",
        date_created=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        market="COMMODITIES",
        asset="XAUUSD",
        timeframe="D1",
        research_class="CLASS-IV",
        market_condition="Multi-day volatility compression regime where Daily True Range is the narrowest of the last 4 days (NR4)",
        observation="Stylized Fact QROS-OBS-020 & Pattern QROS-PAT-002: Daily NR4 compression precedes a 38% increase in 3-day realized price dispersion across 14 years (N=312, p < 0.001).",
        hypothesis_statement="Directional breakouts from a 4-day range compression (NR4) on D1 continue in the direction of the initial daily breakout over a 3 to 8 day holding window.",
        plausible_rationale="Multi-day range compression reflects temporary supply-demand equilibrium and volatility suppression. When directional order flow breaches the compression boundary, resting stops and momentum participants accelerate expansion.",
        entry_condition="Daily True Range < Min(True Range of prior 3 days) [NR4], followed on day t+1 by price breaking above NR4 High (Long) or below NR4 Low (Short).",
        exit_condition="Exit after 5 D1 bars (5 trading days), or upon 1.5x ATR(20) trailing stop loss.",
        holding_period="3 to 8 D1 bars (3 to 8 trading days)",
        expected_effect="Net annualized Sharpe >= 1.00, Profit Factor >= 1.25 under Class IV macro hurdles.",
        null_hypothesis="H_0: Mean net return of post-NR4 breakout trades is <= 0.0.",
        alternative_hypothesis="H_1: Mean net return of post-NR4 breakout trades is strictly > 0.0 with DSR >= 0.90.",
        required_data="XAUUSD D1 historical dataset with >= 50 discrete NR4 events. Satisfied by v3.0.0 D1 dataset.",
        potential_confounders="Prolonged holiday liquidity droughts causing multiple sequential false NR4 breakouts.",
        transaction_cost_assumptions="Class IV Profile: 20 pts spread, 1.5x slippage multiplier, 0ms latency buffer.",
        research_status="PRE_REGISTERED",
        validation_profile=get_default_profile("CLASS-IV"),
    )
    hypotheses.append(hyp5)

    # 6. QROS-HYP-000006: Cross-Timeframe Macro Trend Filtered Intraday Momentum (Class III)
    hyp6 = HypothesisRecord(
        hypothesis_id="QROS-HYP-000006",
        title="Cross-Timeframe Macro Trend Filtered Intraday Momentum",
        author="QROS Quantitative Research Team",
        date_created=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        market="COMMODITIES",
        asset="XAUUSD",
        timeframe="H1",
        research_class="CLASS-III",
        market_condition="Hourly breakout aligned with Daily 50-day Macro Moving Average trend direction",
        observation="Stylized Fact QROS-OBS-022 & Pattern QROS-PAT-006: H1 24-period breakouts aligned with D1 50-day trend direction produce positive 8-hour forward drift across non-OOS data (N=84, p = 0.012).",
        hypothesis_statement="H1 24-bar high/low breakouts that strictly align with the higher-timeframe Daily macro trend (D1 Close > MA50) exhibit positive directional drift over an 8 to 24 hour holding window.",
        plausible_rationale="Higher-timeframe macro trend alignment filters out false consolidation whipsaws by ensuring lower-timeframe breakout momentum flows in the direction of institutional macro positioning.",
        entry_condition="H1 Close > 24-bar High AND D1 Close > 50-Day MA (Long); H1 Close < 24-bar Low AND D1 Close < 50-Day MA (Short).",
        exit_condition="Exit after 16 H1 bars (16 hours), or trailing stop at 2.0x ATR(24).",
        holding_period="8 to 24 H1 bars (8 to 24 hours)",
        expected_effect="Net annualized Sharpe >= 1.20, Profit Factor >= 1.30 under Class III swing hurdles.",
        null_hypothesis="H_0: Mean net return of trend-aligned H1 breakouts is <= 0.0.",
        alternative_hypothesis="H_1: Mean net return of trend-aligned H1 breakouts is strictly > 0.0 with DSR >= 0.95.",
        required_data="XAUUSD H1 and D1 aligned datasets covering continuous non-OOS history.",
        potential_confounders="Abrupt macro reversal days where D1 trend breaks simultaneously with H1 breakout.",
        transaction_cost_assumptions="Class III Profile: 20 pts spread, 2.0x slippage multiplier, 0ms latency buffer.",
        research_status="PRE_REGISTERED",
        validation_profile=get_default_profile("CLASS-III"),
    )
    hypotheses.append(hyp6)

    return hypotheses


def persist_hypotheses_and_registry(
    hypotheses: List[HypothesisRecord],
    base_dir: Optional[str] = None,
) -> str:
    """Save HypothesisRecords as individual YAML files and update master HYPOTHESIS_REGISTRY.md."""
    if base_dir is None:
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "research", "registry")
        )

    hyp_dir = os.path.join(base_dir, "hypotheses")
    os.makedirs(hyp_dir, exist_ok=True)

    # Save individual YAML files
    for hyp in hypotheses:
        hyp_file = os.path.join(hyp_dir, f"{hyp.hypothesis_id}.yaml")
        with open(hyp_file, "w", encoding="utf-8") as f:
            f.write(hyp.to_yaml())

    # Generate master HYPOTHESIS_REGISTRY.md
    reg_file = os.path.join(base_dir, "HYPOTHESIS_REGISTRY.md")
    lines = [
        "# QROS Master Hypothesis Registry",
        f"**Last Updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        "**Governing Standard:** QROS-STD-HYP-002  ",
        "**Status:** Formal Pre-Registration Baseline  ",
        "",
        "---",
        "",
        "## 1. Registry Summary",
        f"- **Total Pre-Registered Hypotheses:** {len(hypotheses)}",
        "- **Validation Architecture:** Governed by Class-Calibrated Validation Profiles (Classes I–V).",
        "- **Integrity Rule:** All hypotheses are pre-registered *prior* to in-sample parameter fitting or backtest optimization.",
        "",
        "---",
        "",
        "## 2. Active Pre-Registered Hypotheses",
        "",
        "| Hypothesis ID | Title | Asset | TF | Research Class | Status | Quality Gates |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for hyp in hypotheses:
        gates = hyp.validate_quality_standard()
        all_passed = all(gates.values())
        gate_badge = "**[6/6 PASS]**" if all_passed else "**[FAIL]**"
        lines.append(
            f"| [`{hyp.hypothesis_id}`](hypotheses/{hyp.hypothesis_id}.yaml) | {hyp.title} | {hyp.asset} | {hyp.timeframe} | {hyp.research_class} | `{hyp.research_status}` | {gate_badge} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Detailed Hypothesis Specifications",
            "",
        ]
    )

    for hyp in hypotheses:
        lines.extend(
            [
                f"### [{hyp.hypothesis_id}] {hyp.title}",
                f"- **Market / Asset / Timeframe:** {hyp.market} | {hyp.asset} | `{hyp.timeframe}`",
                f"- **Research Class:** `{hyp.research_class}` ({hyp.validation_profile.profile_name if hyp.validation_profile else 'Default'})",
                f"- **Market Condition:** {hyp.market_condition}",
                f"- **Empirical Observation:** {hyp.observation}",
                f"- **Hypothesis Statement:** {hyp.hypothesis_statement}",
                f"- **Economic / Microstructure Rationale:** {hyp.plausible_rationale}",
                f"- **Entry Condition:** `{hyp.entry_condition}`",
                f"- **Exit Condition:** `{hyp.exit_condition}`",
                f"- **Holding Period:** {hyp.holding_period}",
                f"- **Expected Effect:** {hyp.expected_effect}",
                f"- **Null Hypothesis ($H_0$):** `{hyp.null_hypothesis}`",
                f"- **Alternative Hypothesis ($H_1$):** `{hyp.alternative_hypothesis}`",
                f"- **Cost Assumptions:** {hyp.transaction_cost_assumptions}",
                "",
                "---",
                "",
            ]
        )

    with open(reg_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return reg_file
