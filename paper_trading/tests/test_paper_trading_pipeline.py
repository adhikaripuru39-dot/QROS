"""Updated tests for paper trading micro-engines including VWAP, two-phase commit, and lifecycle."""

import pytest
import os
from paper_trading.events import BarEvent, SignalEvent, AllocatedTargetEvent, NetOrderEvent, ExecutionFillEvent, RiskApprovedOrderEvent
from paper_trading.market_data_engine import MarketDataEngine
from paper_trading.strategies.strategy_ob_allday import OrderBlockAllDayStrategy
from paper_trading.strategies.strategy_ob_trend import OrderBlockTrendStrategy
from paper_trading.strategies.strategy_fvg_overlap import FVGOverlapStrategy
from paper_trading.portfolio_allocator_engine import PortfolioAllocatorEngine
from paper_trading.position_netting_engine import PositionNettingEngine
from paper_trading.risk_guard_engine import RiskGuardEngine
from paper_trading.execution_simulator_engine import ExecutionSimulatorEngine
from paper_trading.audit_ledger_engine import AuditLedgerEngine
from paper_trading.orchestrator import PaperTradingOrchestrator


def test_market_data_engine_buffer():
    engine = MarketDataEngine(symbol="XAUUSD", max_buffer_bars=500)
    for i in range(12):
        engine.process_m5_bar(
            timestamp=f"2026-08-25T12:{i*5:02d}:00Z",
            open_p=2500.0 + i,
            high_p=2502.0 + i,
            low_p=2499.0 + i,
            close_p=2501.0 + i,
            volume=100.0,
        )
    df_h1 = engine.get_h1_dataframe()
    assert len(df_h1) == 1
    assert "atr14" in df_h1.columns
    assert "ema50" in df_h1.columns


def test_portfolio_allocator_and_two_phase_netting():
    # 2% Risk on $100,000 Equity = $2,000 Risk
    # SL distance = $10.00 -> $10 * 100 oz = $1,000 risk per lot -> 2.00 Lots
    allocator = PortfolioAllocatorEngine(risk_pct_per_trade=0.02)
    netting = PositionNettingEngine()

    sig1 = SignalEvent(
        strategy_id="STRAT_OB_ALLDAY",
        symbol="XAUUSD",
        timestamp="2026-08-25T13:00:00Z",
        direction=1,
        target_price=2500.0,
        stop_loss=2490.0,
        take_profit=2520.0,
        atr=5.0,
    )
    alloc1 = allocator.on_signal(sig1, current_equity=100_000.0)
    assert alloc1.strategy_targets["STRAT_OB_ALLDAY"] == 2.0

    order1 = netting.process_allocation(alloc1, stop_loss=sig1.stop_loss, take_profit=sig1.take_profit)
    assert order1 is not None
    assert order1.net_direction == 1
    assert order1.order_lots == 2.0
    assert order1.stop_loss == 2490.0
    assert order1.take_profit == 2520.0

    # Simulate broker fill confirmation (Two-phase commit)
    fill1 = ExecutionFillEvent(
        fill_id="FILL-01",
        order_id=order1.order_id,
        timestamp=order1.timestamp,
        symbol=order1.symbol,
        direction=1,
        fill_price=2500.15,
        filled_lots=1.0,
        spread_cost_usd=20.0,
        slippage_cost_usd=5.0,
        commission_usd=0.0,
        realized_pnl_usd=0.0,
        current_balance_usd=99975.0,
        current_equity_usd=99975.0,
    )
    netting.on_fill(fill1)
    assert netting.current_net_position == 1.0


def test_execution_simulator_vwap_and_pnl():
    sim = ExecutionSimulatorEngine(starting_balance_usd=100_000.0, spread_pts=20.0, slippage_pts=5.0)
    
    # 1. Buy 1.0 lot at 2500.0 (Fill at 2500.15)
    order1 = RiskApprovedOrderEvent(
        order_id="ORD-01",
        timestamp="2026-08-25T14:00:00Z",
        symbol="XAUUSD",
        direction=1,
        lots=1.0,
        is_approved=True,
    )
    fill1 = sim.execute_order(order1, current_market_price=2500.0)
    assert fill1 is not None
    assert abs(sim.avg_entry_price - 2500.15) < 1e-4
    assert sim.current_position_lots == 1.0

    # 2. Buy another 1.0 lot at 2510.0 (Fill at 2510.15) -> VWAP should be (2500.15 + 2510.15)/2 = 2505.15
    order2 = RiskApprovedOrderEvent(
        order_id="ORD-02",
        timestamp="2026-08-25T14:05:00Z",
        symbol="XAUUSD",
        direction=1,
        lots=1.0,
        is_approved=True,
    )
    fill2 = sim.execute_order(order2, current_market_price=2510.0)
    assert fill2 is not None
    assert abs(sim.avg_entry_price - 2505.15) < 1e-4
    assert sim.current_position_lots == 2.0

    # 3. Sell 2.0 lots at 2520.0 to close (Fill at 2519.85) -> Realized PnL = (2519.85 - 2505.15) * 2 * 100 = $2940.0
    order3 = RiskApprovedOrderEvent(
        order_id="ORD-03",
        timestamp="2026-08-25T14:30:00Z",
        symbol="XAUUSD",
        direction=-1,
        lots=2.0,
        is_approved=True,
    )
    fill3 = sim.execute_order(order3, current_market_price=2520.0)
    assert fill3 is not None
    assert abs(fill3.realized_pnl_usd - 2940.0) < 1e-2
    assert sim.current_position_lots == 0.0
    assert sim.avg_entry_price == 0.0


def test_orchestrator_end_to_end_pipeline():
    test_log = "paper_trading/logs/TEST_AUDIT_LEDGER.jsonl"
    if os.path.exists(test_log):
        os.remove(test_log)

    orchestrator = PaperTradingOrchestrator(symbol="XAUUSD")
    orchestrator.audit = AuditLedgerEngine(log_path=test_log)

    for i in range(24):
        orchestrator.on_m5_bar(
            timestamp=f"2026-08-25T12:{i*5:02d}:00Z" if i < 12 else f"2026-08-25T13:{(i-12)*5:02d}:00Z",
            open_p=2500.0 + i*0.5,
            high_p=2501.0 + i*0.5,
            low_p=2499.5 + i*0.5,
            close_p=2500.8 + i*0.5,
            volume=500.0,
            spread_pts=20.0,
        )

    assert os.path.exists(test_log)