"""Abstract interfaces for Trade Agent plugins.

Every major component is behind an interface. The core agent loop only
knows these interfaces — never concrete implementations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import (
    Balance,
    Candle,
    Decision,
    Event,
    Indicators,
    MarketContext,
    Order,
    OrderBook,
    OrderResult,
    Position,
    Report,
    SentimentScore,
    Ticker,
)


class DataSourceInterface(ABC):
    """Fetch market data (candles, orderbook, ticker)."""

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        ...

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        ...

    @abstractmethod
    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        ...

    def init(self, config: dict[str, Any]) -> None:
        """Called once on startup with data_source config section."""
        pass

    def shutdown(self) -> None:
        """Called on agent shutdown."""
        pass


class StrategyInterface(ABC):
    """Decide what to do based on market context."""

    @abstractmethod
    def analyze(self, context: MarketContext) -> Decision:
        ...

    def init(self, config: dict[str, Any]) -> None:
        """Called once on startup with strategy config section."""
        pass

    def shutdown(self) -> None:
        pass


class ExchangeInterface(ABC):
    """Execute trades on an exchange."""

    @abstractmethod
    def place_order(self, order: Order) -> OrderResult:
        ...

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str | None = None) -> bool:
        ...

    @abstractmethod
    def get_balance(self) -> Balance:
        ...

    @abstractmethod
    def get_positions(self) -> list[Position]:
        ...

    def init(self, config: dict[str, Any]) -> None:
        pass

    def shutdown(self) -> None:
        pass


class NotifierInterface(ABC):
    """Send alerts to users."""

    @abstractmethod
    def send(self, event: Event) -> bool:
        ...

    @abstractmethod
    def send_report(self, report: Report) -> bool:
        ...

    def init(self, config: dict[str, Any]) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def handle_command(self, command: str, args: list[str]) -> str | None:
        """Handle a user command (e.g., /stop, /status).
        Return response text or None if not handled.
        """
        return None

    def start_polling(self) -> None:
        """Start listening for commands (for bot-style notifiers like Telegram).
        Called once after init. Default: do nothing.
        """
        pass


class SentimentInterface(ABC):
    """Fetch + score news sentiment."""

    @abstractmethod
    def get_sentiment(self, symbol: str) -> SentimentScore | None:
        ...

    def init(self, config: dict[str, Any]) -> None:
        pass

    def shutdown(self) -> None:
        pass


class RiskProfileInterface(ABC):
    """Calculate position size, stop-loss, take-profit, and check risk rules."""

    @abstractmethod
    def calculate_position_size(self, available_capital: float, confidence: int) -> float:
        """Return position size in USD."""
        ...

    @abstractmethod
    def calculate_stop_loss(self, entry_price: float, context: MarketContext) -> float:
        """Return stop-loss price."""
        ...

    @abstractmethod
    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        """Return take-profit price."""
        ...

    @abstractmethod
    def check_risk_rules(self, positions: list[Position], decision: Decision, daily_pnl_pct: float) -> bool:
        """Return True if the trade is allowed, False if it violates risk rules."""
        ...

    def init(self, config: dict[str, Any]) -> None:
        pass

    def shutdown(self) -> None:
        pass


class IndicatorPluginInterface(ABC):
    """Compute technical indicators from candle data."""

    @abstractmethod
    def compute(self, candles: list[Candle], indicator_set: list[str]) -> Indicators:
        ...

    def init(self, config: dict[str, Any]) -> None:
        pass
