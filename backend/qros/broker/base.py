"""Broker adapter interface.

The executor talks to brokers ONLY through this interface. Every method that
can fail returns an explicit result; nothing is assumed to have succeeded just
because a request was submitted.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from qros.risk.sizing import ContractSpec


@dataclass(frozen=True)
class AccountInfo:
    login: str
    server: str
    is_demo: Optional[bool]
    currency: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    leverage: Optional[int]
    trade_allowed: bool


@dataclass(frozen=True)
class BrokerPosition:
    ticket: str
    symbol: str
    side: str
    volume: float
    price_open: float
    price_current: float
    sl: Optional[float]
    tp: Optional[float]
    profit: float
    magic: Optional[int]
    comment: Optional[str]
    time: Optional[datetime]


@dataclass(frozen=True)
class BrokerOrder:
    ticket: str
    symbol: str
    type: str
    volume: float
    price: float
    sl: Optional[float]
    tp: Optional[float]
    comment: Optional[str]


@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: float
    ask: float
    time: datetime


@dataclass(frozen=True)
class OrderRequest:
    client_order_id: str      # unique; embedded in broker comment for duplicate detection
    symbol: str
    side: str                 # buy | sell
    volume: float
    sl: float                 # protective stop is mandatory
    tp: Optional[float] = None
    deviation_points: int = 10
    magic: int = 770001


@dataclass
class OrderResult:
    ok: bool                      # True only if the broker confirmed AND we verified
    ticket: Optional[str] = None
    retcode: Optional[int] = None
    message: str = ""
    fill_price: Optional[float] = None
    filled_volume: Optional[float] = None
    verified: bool = False
    duplicate: bool = False
    details: dict = field(default_factory=dict)


@dataclass
class ConnectionStatus:
    connected: bool
    detail: dict = field(default_factory=dict)
    error: Optional[str] = None


class BrokerAdapter(ABC):
    name: str = "abstract"

    @abstractmethod
    def connect(self) -> ConnectionStatus: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def ping(self) -> ConnectionStatus:
        """Cheap liveness check of terminal + broker connection."""

    @abstractmethod
    def account_info(self) -> Optional[AccountInfo]: ...

    @abstractmethod
    def positions(self) -> Optional[list[BrokerPosition]]:
        """None means 'unknown' (query failed), [] means 'no positions'."""

    @abstractmethod
    def pending_orders(self) -> Optional[list[BrokerOrder]]: ...

    @abstractmethod
    def quote(self, symbol: str) -> Optional[Quote]: ...

    @abstractmethod
    def contract_spec(self, symbol: str) -> Optional[ContractSpec]: ...

    @abstractmethod
    def realized_pnl_since(self, since: datetime) -> Optional[float]:
        """Net realized P/L (profit+commission+swap) of deals since `since`."""

    @abstractmethod
    def find_client_order(self, client_order_id: str) -> Optional[str]:
        """Ticket of an existing position/order/deal tagged with this id, else None."""

    @abstractmethod
    def send_market_order(self, req: OrderRequest) -> OrderResult: ...

    @abstractmethod
    def cancel_order(self, ticket: str) -> OrderResult: ...

    @abstractmethod
    def close_position(self, ticket: str) -> OrderResult: ...

    def historical_deals(self, since: datetime) -> Optional[list[dict]]:
        """Broker-observed executions; None means query unsupported/failed."""
        return None

    def completed_bars(self, symbol: str, timeframe_seconds: int, count: int = 512) -> Optional[list[dict]]:
        return None

    def margin_required(self, symbol: str, side: str, volume: float, price: float) -> Optional[float]:
        """Margin needed for the order; None if unknown (risk gate then rejects in demo/live)."""
        return None


def client_tag(client_order_id: str) -> str:
    """Broker comment tag (MT5 comments are limited to ~31 chars)."""
    return "Q:" + hashlib.sha256(client_order_id.encode()).hexdigest()[:28]


def make_adapter(settings) -> "BrokerAdapter":
    if settings.broker_adapter == "mt5":
        from .mt5_adapter import MT5Adapter
        pw = settings.mt5_password.get_secret_value() if settings.mt5_password else None
        return MT5Adapter(path=settings.mt5_path, login=settings.mt5_login, password=pw,
                          server=settings.mt5_server, allow_orders=settings.order_execution_enabled)
    from .null_adapter import NullAdapter
    return NullAdapter()
