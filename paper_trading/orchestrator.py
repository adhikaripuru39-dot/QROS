"""PaperTradingOrchestrator: Single Responsibility = Event Bus Message Routing."""

from typing import Optional
from paper_trading.market_data_engine import MarketDataEngine
from paper_trading.strategies.strategy_ob_allday import OrderBlockAllDayStrategy
from paper_trading.strategies.strategy_ob_trend import OrderBlockTrendStrategy
from paper_trading.strategies.strategy_fvg_overlap import FVGOverlapStrategy
from paper_trading.portfolio_allocator_engine import PortfolioAllocatorEngine
from paper_trading.position_netting_engine import PositionNettingEngine
from paper_trading.risk_guard_engine import RiskGuardEngine
from paper_trading.execution_simulator_engine import ExecutionSimulatorEngine
from paper_trading.mt5_order_router_engine import MT5OrderRouterEngine
from paper_trading.audit_ledger_engine import AuditLedgerEngine


class PaperTradingOrchestrator:
    """Routes incoming market data sequentially through the micro-engines."""

    def __init__(
        self,
        symbol: str = "XAUUSD",
        enable_mt5_live_routing: bool = False,
        risk_pct_per_trade: float = 0.02,
    ) -> None:
        self.symbol = symbol
        self.enable_mt5_live_routing = enable_mt5_live_routing
        self.market_data = MarketDataEngine(symbol=symbol)
        self.strat_ob_allday = OrderBlockAllDayStrategy()
        self.strat_ob_trend = OrderBlockTrendStrategy()
        self.strat_fvg = FVGOverlapStrategy()
        self.allocator = PortfolioAllocatorEngine(risk_pct_per_trade=risk_pct_per_trade)
        self.netting = PositionNettingEngine()
        self.risk_guard = RiskGuardEngine()
        self.execution = ExecutionSimulatorEngine()
        self.mt5_router = MT5OrderRouterEngine(enabled=enable_mt5_live_routing)
        self.audit = AuditLedgerEngine()

    def sync_terminal_state(self) -> None:
        """Synchronizes netting engine and active strategy states with real MT5 open positions."""
        if not self.enable_mt5_live_routing or not self.mt5_router.MT5_AVAILABLE:
            return

        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol=self.symbol)
            magic_positions = [p for p in positions if p.magic == self.mt5_router.magic_number] if positions else []

            if len(magic_positions) == 0:
                # If no open positions exist in MT5, ensure all strategies and netting engine are reset to FLAT (0)
                if abs(self.netting.current_net_position) > 1e-4:
                    self.netting.current_net_position = 0.0
                    self.allocator.current_strategy_targets = {k: 0.0 for k in self.allocator.current_strategy_targets}
                    self.strat_ob_allday.active_trade = None
                    self.strat_ob_trend.active_trade = None
                    self.strat_fvg.active_trade = None
            else:
                total_lots = sum(p.volume if p.type == mt5.ORDER_TYPE_BUY else -p.volume for p in magic_positions)
                self.netting.current_net_position = round(total_lots, 2)
        except Exception as e:
            print(f"[WARN] Failed to sync MT5 positions: {e}")

    def on_m5_bar(self, timestamp: str, open_p: float, high_p: float, low_p: float, close_p: float, volume: float, spread_pts: float = 20.0):
        # 1. Sync terminal state with physical MT5 broker positions
        self.sync_terminal_state()

        # 2. Market Data Ingestion
        bar = self.market_data.process_m5_bar(timestamp, open_p, high_p, low_p, close_p, volume, spread_pts)
        df_h1 = self.market_data.get_h1_dataframe()
        self.audit.record_event("BAR_EVENT", bar)

        # 3. Strategy Signal Generation (Top 3 Strategies)
        sig1 = self.strat_ob_allday.evaluate_bar(bar, df_h1)
        sig2 = self.strat_ob_trend.evaluate_bar(bar, df_h1)
        sig3 = self.strat_fvg.evaluate_bar(bar, df_h1)

        # Determine current account equity for 2% dynamic risk sizing
        current_equity = self.execution.equity_usd
        if self.enable_mt5_live_routing and self.mt5_router.MT5_AVAILABLE:
            try:
                import MetaTrader5 as mt5
                acc = mt5.account_info()
                if acc is not None and acc.equity > 0:
                    current_equity = float(acc.equity)
            except Exception:
                pass

        # 4. Sequentially process signals without collision or overwriting
        for sig in [sig1, sig2, sig3]:
            if sig is None:
                continue

            self.audit.record_event("SIGNAL_EVENT", sig)

            # Portfolio Allocation
            alloc = self.allocator.on_signal(sig, current_equity=current_equity)
            self.audit.record_event("ALLOCATED_TARGET_EVENT", alloc)

            # Position Netting with Stop Loss and Take Profit
            net_order = self.netting.process_allocation(alloc, stop_loss=sig.stop_loss, take_profit=sig.take_profit)
            if net_order is None:
                continue

            self.audit.record_event("NET_ORDER_EVENT", net_order)

            # Risk Guard
            approved_order = self.risk_guard.validate_order(net_order, current_spread_pts=bar.spread_pts)
            self.audit.record_event("RISK_APPROVED_EVENT", approved_order)

            # Order Routing (MT5 Live vs. Simulator)
            if approved_order.is_approved:
                fill = None
                if self.enable_mt5_live_routing:
                    # Submit physical market order to MT5 with exact SL & TP levels
                    fill = self.mt5_router.send_order(
                        order=approved_order,
                        stop_loss=approved_order.stop_loss,
                        take_profit=approved_order.take_profit,
                    )

                # Fallback or standard simulation execution
                if fill is None:
                    fill = self.execution.execute_order(approved_order, current_market_price=bar.close)

                if fill:
                    # Update netting engine of confirmed fill (Two-Phase Commit)
                    self.netting.on_fill(fill)
                    self.audit.record_event("EXECUTION_FILL_EVENT", fill)
