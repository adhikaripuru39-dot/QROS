"""Prop Firm Risk Governance and Rule Enforcement."""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PropFirmConfig:
    """Configuration for Prop Firm limits (e.g. Funded Next, Funding Pips)."""
    max_daily_drawdown_pct: float = 0.04  # 4%
    max_total_drawdown_pct: float = 0.08  # 8%
    starting_balance: float = 100000.0
    daily_reset_time_utc: str = "21:00" # Typical prop firm daily reset (5 PM EST -> 21:00 UTC during standard time)


class PropFirmRiskManager:
    """
    Scientific implementation of Prop Firm Risk Management.
    Ensures that mark-to-market equity does not breach daily or max drawdown limits.
    """

    def __init__(self, config: PropFirmConfig):
        self.config = config
        self.initial_balance = config.starting_balance

        # State tracking
        self.current_equity = config.starting_balance
        self.current_balance = config.starting_balance
        self.daily_start_equity = config.starting_balance
        self.highest_equity = config.starting_balance

        self.is_account_blown = False
        self.blow_reason = ""
        self.last_processed_date: Optional[datetime.date] = None

    def _check_daily_reset(self, current_time: pd.Timestamp):
        """Reset daily starting equity at the firm's specified rollover time."""
        current_date = current_time.date()
        # simplified check: if day changes, we update daily_start_equity
        if self.last_processed_date is None:
            self.last_processed_date = current_date
            return

        if current_date != self.last_processed_date:
            # According to most prop firms (like FundedNext/FundingPips), daily drawdown
            # is calculated based on the starting equity OR balance of the day, whichever is HIGHER.
            # However, standard practice is to use the starting equity/balance at 5 PM EST.
            # We approximate this by resetting at the start of a new trading day.
            self.daily_start_equity = max(self.current_balance, self.current_equity)
            self.last_processed_date = current_date

    def update_mark_to_market(self, timestamp: pd.Timestamp, unrealized_pnl: float, realized_pnl: float = 0.0) -> Tuple[bool, str]:
        """
        Updates the account equity and checks for rule breaches.

        Parameters:
        - timestamp: The current bar's timestamp.
        - unrealized_pnl: Open floating PnL (to assess intra-trade drawdown).
        - realized_pnl: Any closed profit/loss since last check.

        Returns:
        - Tuple (is_breached, reason)
        """
        if self.is_account_blown:
            return True, self.blow_reason

        self._check_daily_reset(timestamp)

        # Update balance and equity
        self.current_balance += realized_pnl
        self.current_equity = self.current_balance + unrealized_pnl

        if self.current_equity > self.highest_equity:
            self.highest_equity = self.current_equity

        # Check Max Drawdown (Calculated from initial balance)
        max_dd_amount = self.initial_balance * self.config.max_total_drawdown_pct
        max_allowed_equity = self.initial_balance - max_dd_amount

        if self.current_equity <= max_allowed_equity:
            self.is_account_blown = True
            self.blow_reason = f"Max Drawdown Breached at {timestamp}. Equity: {self.current_equity:.2f} <= Limit: {max_allowed_equity:.2f}"
            return True, self.blow_reason

        # Check Daily Drawdown (Calculated from daily starting equity)
        daily_dd_amount = self.daily_start_equity * self.config.max_daily_drawdown_pct
        daily_allowed_equity = self.daily_start_equity - daily_dd_amount

        if self.current_equity <= daily_allowed_equity:
            self.is_account_blown = True
            self.blow_reason = f"Daily Drawdown Breached at {timestamp}. Equity: {self.current_equity:.2f} <= Limit: {daily_allowed_equity:.2f}"
            return True, self.blow_reason

        return False, ""

    def can_open_trade(self) -> bool:
        """Checks if the account is allowed to open new trades."""
        return not self.is_account_blown
