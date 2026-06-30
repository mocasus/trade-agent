"""CCXT-based exchange execution plugin."""

from __future__ import annotations

from typing import Any

import ccxt

from trade_agent.interfaces import ExchangeInterface
from trade_agent.models import Balance, Order, OrderResult, OrderSide, Position


class CCXTExchange(ExchangeInterface):
    def __init__(self):
        self.exchange: ccxt.Exchange | None = None

    def init(self, config: dict[str, Any]) -> None:
        exchange_name = config.get("exchange", "binance")
        exchange_cls = getattr(ccxt, exchange_name, None)
        if not exchange_cls:
            raise ValueError(f"Exchange {exchange_name} not found in ccxt")

        self.exchange = exchange_cls(
            {
                "apiKey": config.get("api_key", ""),
                "secret": config.get("api_secret", ""),
                "enableRateLimit": config.get("rate_limit", True),
            }
        )
        if config.get("testnet", True) and hasattr(self.exchange, "set_sandbox_mode"):
            self.exchange.set_sandbox_mode(True)

    def place_order(self, order: Order) -> OrderResult:
        side = "buy" if order.side == OrderSide.BUY else "sell"
        try:
            params = {}
            if order.stop_loss:
                params["stopLoss"] = {"triggerPrice": order.stop_loss}
            if order.take_profit:
                params["takeProfit"] = {"triggerPrice": order.take_profit}

            result = self.exchange.create_order(
                symbol=order.symbol,
                type=order.type.value,
                side=side,
                amount=order.amount,
                price=order.price or None,
                params=params,
            )
            return OrderResult(
                order_id=result.get("id", ""),
                symbol=order.symbol,
                side=side,
                type=order.type.value,
                amount=result.get("amount", order.amount),
                price=result.get("price", order.price or 0),
                fee=result.get("fee", {}).get("cost", 0),
                status="filled" if result.get("status") == "closed" else "open",
            )
        except Exception as e:
            return OrderResult(
                order_id="",
                symbol=order.symbol,
                side=side,
                type=order.type.value,
                amount=order.amount,
                price=order.price or 0,
                status="error",
                error=str(e),
            )

    def cancel_order(self, order_id: str, symbol: str | None = None) -> bool:
        try:
            self.exchange.cancel_order(order_id, symbol or "")
            return True
        except Exception:
            return False

    def get_balance(self) -> Balance:
        try:
            b = self.exchange.fetch_balance()
            total = b.get("total", {})
            usd_total = total.get("USDT", 0) or total.get("USD", 0) or 0
            free = b.get("free", {})
            usd_free = free.get("USDT", 0) or free.get("USD", 0) or 0
            return Balance(
                total_usd=float(usd_total),
                available_usd=float(usd_free),
                reserved_usd=float(usd_total) - float(usd_free),
                assets={k: float(v) for k, v in total.items() if v and v > 0},
            )
        except Exception:
            return Balance()

    def get_positions(self) -> list[Position]:
        # Spot exchanges don't have "positions" — return open orders as positions
        return []

    def shutdown(self) -> None:
        if self.exchange:
            self.exchange.close()


def register():
    return {
        "name": "ccxt",
        "class": CCXTExchange,
        "description": "CCXT exchange (100+ exchanges)",
    }
