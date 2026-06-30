"""Bybit futures exchange adapter."""

from __future__ import annotations
from trade_agent.interfaces import ExchangeInterface
from trade_agent.models import Order, Position, Balance


class BybitFuturesExchange(ExchangeInterface):
    """Bybit USDT perpetual futures via ccxt."""

    def __init__(
        self,
        api_key: str = "",
        secret: str = "",
        leverage: int = 10,
        margin_mode: str = "cross",
        position_mode: str = "one-way",
        testnet: bool = False,
    ):
        import ccxt

        self.exchange = ccxt.bybit(
            {
                "apiKey": api_key,
                "secret": secret,
                "options": {"defaultType": "swap"},
            }
        )
        if testnet:
            self.exchange.set_sandbox_mode(True)
        self.leverage = leverage
        self.margin_mode = margin_mode
        self._position_mode_set = position_mode == "one-way"

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        return self.exchange.set_leverage(leverage, symbol)

    def set_margin_mode(self, symbol: str, mode: str) -> dict:
        return self.exchange.set_margin_mode(mode, symbol)

    def get_balance(self) -> Balance:
        bal = self.exchange.fetch_balance({"type": "swap"})
        free = float(bal.get("free", {}).get("USDT", 0))
        used = float(bal.get("used", {}).get("USDT", 0))
        total = float(bal.get("total", {}).get("USDT", 0))
        return Balance(asset="USDT", free=free, used=used, total=total)

    def get_positions(self, symbols: list[str] | None = None) -> list[Position]:
        positions = []
        for sym in symbols or []:
            pos = self.exchange.fetch_positions([sym])
            for p in pos:
                if float(p.get("contracts", 0)) > 0:
                    positions.append(
                        Position(
                            symbol=p["symbol"],
                            side=p["side"],
                            entry_price=float(p["entryPrice"]),
                            quantity=float(p["contracts"]),
                            unrealized_pnl=float(p.get("unrealizedPnl", 0)),
                            leverage=int(p.get("leverage", self.leverage)),
                        )
                    )
        return positions

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: float | None = None,
        params: dict | None = None,
    ) -> Order:
        p = params or {}
        p["leverage"] = self.leverage
        result = self.exchange.create_order(
            symbol, order_type, side, quantity, price or 0, p
        )
        return Order(
            order_id=result["id"],
            symbol=result["symbol"],
            side=result["side"],
            order_type=result["type"],
            quantity=float(result["amount"]),
            price=float(result.get("price", 0) or 0),
            status=result["status"],
            timestamp=result["timestamp"],
        )

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        self.exchange.cancel_order(order_id, symbol)
        return True

    def get_order(self, order_id: str, symbol: str) -> Order:
        o = self.exchange.fetch_order(order_id, symbol)
        return Order(
            order_id=o["id"],
            symbol=o["symbol"],
            side=o["side"],
            order_type=o["type"],
            quantity=float(o["amount"]),
            price=float(o.get("price", 0) or 0),
            status=o["status"],
            timestamp=o["timestamp"],
        )

    def get_ticker(self, symbol: str) -> dict:
        return self.exchange.fetch_ticker(symbol)
