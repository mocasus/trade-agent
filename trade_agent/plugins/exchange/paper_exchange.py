"""Paper trading exchange simulator."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from trade_agent.interfaces import ExchangeInterface
from trade_agent.models import Balance, Order, OrderResult, OrderSide, Position


class PaperExchange(ExchangeInterface):
    def __init__(self):
        self._balance = Balance(total_usd=10000.0, available_usd=10000.0)
        self._positions: list[Position] = []
        self._orders: dict[str, OrderResult] = {}
        self._fee_pct: float = 0.1
        self._slippage_pct: float = 0.05
        self._counter: int = 0

    def init(self, config: dict[str, Any]) -> None:
        self._balance.total_usd = float(config.get("initial_capital", 10000))
        self._balance.available_usd = self._balance.total_usd
        self._fee_pct = float(config.get("fee_pct", 0.1))
        self._slippage_pct = float(config.get("slippage_pct", 0.05))

    def place_order(self, order: Order) -> OrderResult:
        self._counter += 1
        order_id = f"PAPER-{self._counter}"
        now = datetime.now().timestamp()

        # Get current price (from order.price or mock)
        base_price = order.price or 50000.0  # fallback mock price
        slippage = base_price * (self._slippage_pct / 100)
        exec_price = (
            base_price + slippage
            if order.side == OrderSide.BUY
            else base_price - slippage
        )
        fee = order.amount * exec_price * (self._fee_pct / 100)

        if order.side == OrderSide.BUY:
            cost = order.amount * exec_price + fee
            if cost > self._balance.available_usd:
                return OrderResult(
                    order_id=order_id,
                    symbol=order.symbol,
                    side="buy",
                    type=order.type.value,
                    amount=0,
                    price=exec_price,
                    status="error",
                    error="Insufficient paper balance",
                    fee=0,
                    timestamp=now,
                )
            self._balance.available_usd -= cost
            self._positions.append(
                Position(
                    symbol=order.symbol,
                    side="long",
                    entry_price=exec_price,
                    amount=order.amount,
                    current_price=exec_price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    opened_at=now,
                )
            )
        elif order.side == OrderSide.SELL:
            # Find and close matching position
            closed = False
            for i, pos in enumerate(self._positions):
                if pos.symbol == order.symbol and pos.side == "long":
                    proceeds = order.amount * exec_price - fee
                    self._balance.available_usd += proceeds
                    self._positions.pop(i)
                    closed = True
                    break
            if not closed:
                return OrderResult(
                    order_id=order_id,
                    symbol=order.symbol,
                    side="sell",
                    type=order.type.value,
                    amount=0,
                    price=exec_price,
                    status="error",
                    error="No position to close",
                    fee=0,
                    timestamp=now,
                )

        return OrderResult(
            order_id=order_id,
            symbol=order.symbol,
            side="buy" if order.side == OrderSide.BUY else "sell",
            type=order.type.value,
            amount=order.amount,
            price=exec_price,
            fee=fee,
            status="filled",
            timestamp=now,
        )

    def cancel_order(self, order_id: str, symbol: str | None = None) -> bool:
        if order_id in self._orders:
            del self._orders[order_id]
            return True
        return False

    def get_balance(self) -> Balance:
        total = self._balance.available_usd
        for pos in self._positions:
            total += pos.amount * pos.current_price
        return Balance(
            total_usd=total,
            available_usd=self._balance.available_usd,
            reserved_usd=total - self._balance.available_usd,
        )

    def get_positions(self) -> list[Position]:
        return list(self._positions)

    def shutdown(self) -> None:
        pass


def register():
    return {
        "name": "paper",
        "class": PaperExchange,
        "description": "Paper trading simulator (no real funds)",
    }
