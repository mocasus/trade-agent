"""CCXT-based data source plugin."""

from __future__ import annotations

from typing import Any

import ccxt

from trade_agent.interfaces import DataSourceInterface
from trade_agent.models import Candle, OrderBook, Ticker


class CCXTSource(DataSourceInterface):
    """Fetch market data via ccxt (supports 100+ exchanges)."""

    def __init__(self):
        self.exchange: ccxt.Exchange | None = None
        self._exchange_name: str = "binance"
        self._testnet: bool = True

    def init(self, config: dict[str, Any]) -> None:
        self._exchange_name = config.get("exchange", "binance")
        self._testnet = config.get("testnet", True)
        api_key = config.get("api_key", "")
        api_secret = config.get("api_secret", "")

        exchange_cls = getattr(ccxt, self._exchange_name, None)
        if not exchange_cls:
            raise ValueError(f"Exchange {self._exchange_name} not found in ccxt")

        self.exchange = exchange_cls(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": config.get("rate_limit", True),
            }
        )

        if self._testnet and hasattr(self.exchange, "set_sandbox_mode"):
            self.exchange.set_sandbox_mode(True)

    def get_candles(
        self, symbol: str, timeframe: str, limit: int = 200
    ) -> list[Candle]:
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        return [
            Candle(
                timestamp=row[0] / 1000,
                open=row[1],
                high=row[2],
                low=row[3],
                close=row[4],
                volume=row[5],
            )
            for row in ohlcv
        ]

    def get_ticker(self, symbol: str) -> Ticker:
        t = self.exchange.fetch_ticker(symbol)
        return Ticker(
            symbol=symbol,
            last_price=t.get("last", 0),
            bid=t.get("bid", 0),
            ask=t.get("ask", 0),
            volume_24h=t.get("baseVolume", 0),
            change_pct_24h=t.get("change", 0) or 0,
        )

    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        ob = self.exchange.fetch_order_book(symbol, limit=depth)
        return OrderBook(
            symbol=symbol,
            bids=ob.get("bids", []),
            asks=ob.get("asks", []),
        )

    def shutdown(self) -> None:
        if self.exchange:
            self.exchange.close()


def register():
    return {
        "name": "ccxt",
        "class": CCXTSource,
        "description": "CCXT data source (100+ exchanges)",
    }
