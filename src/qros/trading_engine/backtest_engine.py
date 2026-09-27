"""Core Backtesting Engine bridging Data, Risk Management, Costs, and Stats."""

import pandas as pd
import numpy as np
from typing import Callable, Dict, Any, Optional

from qros.trading_engine.prop_firm_rules import PropFirmRiskManager, PropFirmConfig
from qros.trading_engine.news_filter import MT5NewsFilter
from qros.pipeline.costs import TransactionCostModel, CostModelConfig
from qros.pipeline.evaluation import evaluate_statistical_profile
from qros.schemas.validation_profile import ValidationProfile

class ScientificBacktestEngine:
    """
    Event-driven simulation loop linking market data, strategies, and strict Prop Firm governance.
    """

    def __init__(self,
                 data: pd.DataFrame,
                 strategy_func: Callable[[pd.DataFrame, int], int], # Returns 1 (Buy), -1 (Sell), 0 (Hold)
                 prop_config: Optional[PropFirmConfig] = None,
                 cost_model: Optional[TransactionCostModel] = None,
                 news_filter: Optional[MT5NewsFilter] = None,
                 validation_profile: Optional[ValidationProfile] = None):
        """
        Parameters:
        - data: OHLCV DataFrame indexed by timezone-aware timestamps.
        - strategy_func: A function taking (df, current_idx) returning signal.
        """
        self.data = data.copy()
        self.strategy = strategy_func
        self.symbol = "XAUUSD"

        self.risk_manager = PropFirmRiskManager(prop_config or PropFirmConfig())
        self.cost_model = cost_model or TransactionCostModel(CostModelConfig())
        self.news_filter = news_filter or MT5NewsFilter()
        self.validation_profile = validation_profile

        self.results: Dict[str, Any] = {}
        self.trade_log = []

        # State
        self.position = 0 # 1 long, -1 short, 0 flat
        self.entry_price = 0.0
        self.entry_idx = 0
        self.entry_time = None

    def run(self) -> pd.Series:
        """
        Runs the loop over the DataFrame.
        Returns a Pandas Series of net returns (in basis points or nominal,
        depending on cost model setup) per trade, compatible with qros.pipeline.evaluation.
        """
        net_returns = []
        equity_curve = [self.risk_manager.initial_balance]

        for i in range(len(self.data)):
            current_bar = self.data.iloc[i]
            current_time = self.data.index[i]

            # 1. Mark to Market update for Prop Firm Risk Manager
            if self.position != 0:
                # Approximate floating PnL (assuming 1 lot for simplicity, scalable later)
                price_diff = (current_bar['close'] - self.entry_price) if self.position == 1 else (self.entry_price - current_bar['close'])
                floating_pnl = price_diff * self.cost_model.config.point_value_multiplier
            else:
                floating_pnl = 0.0

            is_blown, reason = self.risk_manager.update_mark_to_market(current_time, floating_pnl, realized_pnl=0.0)

            if is_blown:
                print(f"ACCOUNT BLOWN: {reason}")
                # Force close position if open
                if self.position != 0:
                    self._close_position(current_bar, current_time, i, net_returns)
                break # Stop trading forever

            # 2. Check for Exits
            signal = self.strategy(self.data, i)

            if self.position != 0:
                # Simplified exit logic: reverse signal closes position
                if (self.position == 1 and signal == -1) or (self.position == -1 and signal == 1) or signal == 0:
                    self._close_position(current_bar, current_time, i, net_returns)

            # 3. Check for Entries (if flat and risk allows)
            if self.position == 0 and signal != 0:
                if self.risk_manager.can_open_trade() and self.news_filter.is_trading_allowed(current_time, symbol=self.symbol):
                    self.position = signal
                    self.entry_price = current_bar['close']
                    self.entry_idx = i
                    self.entry_time = current_time

            equity_curve.append(self.risk_manager.current_equity)

        # Force close at end of data if still open
        if self.position != 0 and not self.risk_manager.is_account_blown:
            self._close_position(self.data.iloc[-1], self.data.index[-1], len(self.data)-1, net_returns)

        self.results['equity_curve'] = equity_curve
        self.results['trade_log'] = self.trade_log

        return pd.Series(net_returns)

    def _close_position(self, current_bar, current_time, i, net_returns_list):
        """Helper to close position, apply costs, and log trade."""
        exit_price = current_bar['close']

        # Gross return in points
        gross_pts = (exit_price - self.entry_price) if self.position == 1 else (self.entry_price - exit_price)

        # Holding duration
        holding_time = current_time - self.entry_time
        holding_days = holding_time.total_seconds() / (24 * 3600)

        # Calculate Friction (Costs)
        friction_pts = self.cost_model.calculate_total_friction_pts(
            is_stress_test=False, # Could be toggled
            holding_days=holding_days,
            is_long=(self.position == 1)
        )

        net_pts = gross_pts - friction_pts

        # Convert points to currency/return basis
        net_return_val = net_pts * self.cost_model.config.point_value_multiplier

        # Update risk manager with REALIZED PnL
        self.risk_manager.update_mark_to_market(current_time, unrealized_pnl=0.0, realized_pnl=net_return_val)

        net_returns_list.append(net_return_val)

        self.trade_log.append({
            'entry_time': self.entry_time,
            'exit_time': current_time,
            'direction': 'LONG' if self.position == 1 else 'SHORT',
            'entry_price': self.entry_price,
            'exit_price': exit_price,
            'gross_pts': gross_pts,
            'friction_pts': friction_pts,
            'net_return': net_return_val
        })

        # Reset state
        self.position = 0
        self.entry_price = 0.0
        self.entry_idx = 0
        self.entry_time = None

    def evaluate_statistics(self, net_returns_series: pd.Series, hypothesis_id: str = "BACKTEST-001"):
        """
        Pipes the output back into the qros.pipeline.evaluation module
        to check DSR, Bootstrap CIs, etc.
        """
        if self.validation_profile is None:
            raise ValueError("ValidationProfile must be provided to evaluate statistics.")

        returns_array = net_returns_series.to_numpy()

        if len(returns_array) == 0:
            print("No trades generated.")
            return None

        result = evaluate_statistical_profile(
            returns_net=returns_array,
            validation_profile=self.validation_profile,
            hypothesis_id=hypothesis_id,
            trial_count_k=1, # Single run
            observation_count_t=len(self.data)
        )
        return result
