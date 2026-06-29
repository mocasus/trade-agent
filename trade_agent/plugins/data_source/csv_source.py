"""CSV-based data source for backtesting."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from trade_agent.interfaces import DataSourceInterface
from trade_agent.models import Candle, OrderBook, Ticker


class CSVSource(DataSourceInterface):
    def __init__(self):
        self._path: Path | None = None
        self._candles: list[Candle] = []
        self._current_idx: int = 0

    def init(self, config: dict[str, Any]) -> None:
        self._path = Path(config.get("csv_path", "")).expanduser()
        if not self._path.exists():
            raise FileNotFoundError(f"CSV file not found: {self._path}")
        self._load_csv()

    def _load_csv(self) -> None:
        with self._path.open("r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._candles.append(Candle(
                    timestamp=float(row.get("timestamp", 0)),
                    open=float(row.get("open", 0)),
                    high=float(row.get("high", 0)),
                    low=float(row.get("low", 0)),
                    close=float(row.get("close", 0)),
                    volume=float(row.get("volume", 0)),
                ))

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        return self._candles[-limit:]

    def get_ticker(self, symbol: str) -> Ticker:
        if self._candles:
            last = self._candles[-1]
            return Ticker(symbol=symbol, last_price=last.close, bid=last.close, ask=last.close, volume_24h=0, change_pct_24h=0)
        return Ticker(symbol=symbol, last_price=0, bid=0, ask=0, volume_24h=0, change_pct_24h=0)

    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        return OrderBook(symbol=symbol, bids=[], asks=[])

    def shutdown(self) -> None:
        pass


def register():
    return {"name": "csv", "class": CSVSource, "description": "CSV file data source for backtesting"}
