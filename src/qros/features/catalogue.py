"""Part 4 ch.2: Comprehensive Institutional Feature Taxonomy registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureDeclaration:
    """A feature category declared in the handbook taxonomy."""

    name: str
    formula: str
    logic: str
    risk: str


FEATURE_DECLARATIONS: tuple[FeatureDeclaration, ...] = (
    FeatureDeclaration(
        name="log_returns_vol",
        formula="r_t = ln(P_t / P_{t-1}), Vol_w = std(r_t) * sqrt(252)",
        logic="Captures price momentum, variance risk premium, and volatility clustering.",
        risk="Low overfitting risk; highly interpretable benchmark.",
    ),
    FeatureDeclaration(
        name="order_book_imbalance",
        formula="OBI_t = (V_bid,1 - V_ask,1) / (V_bid,1 + V_ask,1)",
        logic="Measures short-term order book supply/demand asymmetry.",
        risk="High frequency decay; susceptible to spoofing quotes.",
    ),
    FeatureDeclaration(
        name="vwap",
        formula="VWAP_t = sum(P_i * V_i) / sum(V_i)",
        logic="Benchmark for institutional execution and intraday price anchors.",
        risk="Requires intraday reset; structural regime dependent.",
    ),
    FeatureDeclaration(
        name="garman_klass_vol",
        formula="sigma_GK^2 = 0.5*(ln(H/L))^2 - (2*ln(2)-1)*(ln(C/O))^2",
        logic="Efficient intraday volatility estimator using OHLC bounds.",
        risk="Underestimates jump diffusion volatility during opening gaps.",
    ),
    FeatureDeclaration(
        name="vpin",
        formula="VPIN = sum(|V_B - V_S|) / (N_bars * V_bar)",
        logic="Volume-Synchronized Probability of Toxicity measuring adverse selection.",
        risk="Requires optimal volume bar size tuning; computationally intensive.",
    ),
    FeatureDeclaration(
        name="cross_asset_relative_momentum",
        formula="Rel_Mom = r_{asset,w} - r_{benchmark,w}",
        logic="Captures capital rotation across sectors and risk-on/risk-off dynamics.",
        risk="Prone to regime breaks during systemic market crashes.",
    ),
    FeatureDeclaration(
        name="gamma_exposure",
        formula="GEX = sum(Gamma_i * OpenInterest_i * S^2 * 0.01)",
        logic="Quantifies options dealer hedging flow (volatility suppression vs expansion).",
        risk="Requires accurate options chain data; option strike clustering noise.",
    ),
)