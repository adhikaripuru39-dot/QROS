"""MT5OrderRouterEngine: Single Responsibility = Route Physical Orders to MetaTrader 5 Terminal."""

from typing import Optional
from paper_trading.events import RiskApprovedOrderEvent, ExecutionFillEvent

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class MT5OrderRouterEngine:
    """Submits physical Market/Deal orders to MetaTrader 5 Terminal."""

    MT5_AVAILABLE = MT5_AVAILABLE

    def __init__(self, magic_number: int = 100101, comment: str = "QROS-LIVE-ENGINE", enabled: bool = False) -> None:
        self.magic_number = magic_number
        self.comment = comment
        self.MT5_AVAILABLE = MT5_AVAILABLE
        self.enabled = enabled

    def send_order(
        self,
        order: RiskApprovedOrderEvent,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        deviation: int = 20,
    ) -> Optional[ExecutionFillEvent]:
        """Routes approved order to connected MetaTrader 5 terminal via order_send."""
        if not self.enabled or not order.is_approved or order.lots <= 0:
            return None

        if not MT5_AVAILABLE:
            print("[WARN] MetaTrader5 library not available. Falling back to software fill.")
            return None

        symbol_info = mt5.symbol_info(order.symbol)
        if symbol_info is None:
            print(f"[ERROR] Symbol {order.symbol} not found in MT5 Market Watch.")
            return None

        tick = mt5.symbol_info_tick(order.symbol)
        if tick is None:
            print(f"[ERROR] Cannot fetch tick for {order.symbol}.")
            return None

        is_buy = order.direction > 0
        order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        price = tick.ask if is_buy else tick.bid

        # Check for open positions with our magic number to close in MT5 hedging mode
        open_positions = mt5.positions_get(symbol=order.symbol)
        target_pos = None
        if open_positions:
            for pos in open_positions:
                if pos.magic == self.magic_number:
                    # Closing BUY position with a SELL deal, or closing SELL position with a BUY deal
                    if (not is_buy and pos.type == mt5.ORDER_TYPE_BUY) or (is_buy and pos.type == mt5.ORDER_TYPE_SELL):
                        target_pos = pos
                        break

        # Prepare MT5 order request structure
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": order.symbol,
            "volume": float(order.lots),
            "type": order_type,
            "price": float(price),
            "sl": float(stop_loss) if stop_loss > 0 else 0.0,
            "tp": float(take_profit) if take_profit > 0 else 0.0,
            "deviation": int(deviation),
            "magic": int(self.magic_number),
            "comment": self.comment,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # If liquidating an existing open ticket on a Hedging account, attach position ticket
        if target_pos is not None:
            request["position"] = target_pos.ticket

        result = mt5.order_send(request)
        if result is None:
            print(f"[ERROR] mt5.order_send returned None: {mt5.last_error()}")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[ERROR] MT5 Order Failed: retcode={result.retcode}, comment={result.comment}")
            return None

        print(f"[MT5 LIVE DEAL FILLED] Ticket: {result.order} | {order.symbol} "
              f"{'BUY' if is_buy else 'SELL'} {order.lots} lots @ {result.price:.2f} | SL: {stop_loss:.2f} TP: {take_profit:.2f}")

        acc = mt5.account_info()
        balance = acc.balance if acc else 100_000.0
        equity = acc.equity if acc else 100_000.0

        return ExecutionFillEvent(
            fill_id=f"MT5-DEAL-{result.deal if result.deal else result.order}",
            order_id=order.order_id,
            timestamp=order.timestamp,
            symbol=order.symbol,
            direction=order.direction,
            fill_price=result.price,
            filled_lots=result.volume,
            spread_cost_usd=0.0,
            slippage_cost_usd=0.0,
            commission_usd=0.0,
            realized_pnl_usd=0.0,
            current_balance_usd=balance,
            current_equity_usd=equity,
        )
