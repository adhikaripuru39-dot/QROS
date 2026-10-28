"""Adapter used when no broker is configured. Always reports disconnected."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .base import (AccountInfo, BrokerAdapter, BrokerOrder, BrokerPosition, ConnectionStatus,
                   OrderRequest, OrderResult, Quote)

_MSG = "no broker adapter configured (QROS_BROKER_ADAPTER=none)"


class NullAdapter(BrokerAdapter):
    name = "none"

    def connect(self) -> ConnectionStatus:
        return ConnectionStatus(False, {"adapter": "none"}, _MSG)

    def disconnect(self) -> None:
        return None

    def ping(self) -> ConnectionStatus:
        return self.connect()

    def account_info(self) -> Optional[AccountInfo]:
        return None

    def positions(self) -> Optional[list[BrokerPosition]]:
        return None

    def pending_orders(self) -> Optional[list[BrokerOrder]]:
        return None

    def quote(self, symbol: str) -> Optional[Quote]:
        return None

    def contract_spec(self, symbol: str):
        return None

    def realized_pnl_since(self, since: datetime) -> Optional[float]:
        return None

    def find_client_order(self, client_order_id: str) -> Optional[str]:
        return None

    def send_market_order(self, req: OrderRequest) -> OrderResult:
        return OrderResult(False, message=_MSG)

    def cancel_order(self, ticket: str) -> OrderResult:
        return OrderResult(False, message=_MSG)

    def close_position(self, ticket: str) -> OrderResult:
        return OrderResult(False, message=_MSG)
