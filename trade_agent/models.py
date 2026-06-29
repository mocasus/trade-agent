"""Data models for Trade Agent.

All data structures used across interfaces, plugins, and the main loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_ALL = "CLOSE_ALL"
    SET_STOP_LOSS = "SET_STOP_LOSS"
    SET_TRAILING_STOP = "SET_TRAILING_STOP"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Candle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)


@dataclass
class Ticker:
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume_24h: float
    change_pct_24h: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class OrderBook:
    symbol: str
    bids: list[list[float]]  # [[price, amount], ...]
    asks: list[list[float]]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Indicators:
    """Technical indicator values for a symbol."""
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    atr: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "rsi": self.rsi,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "ema_20": self.ema_20,
            "ema_50": self.ema_50,
            "ema_200": self.ema_200,
            "bb_upper": self.bb_upper,
            "bb_middle": self.bb_middle,
            "bb_lower": self.bb_lower,
            "atr": self.atr,
        }
        d.update(self.extra)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class SentimentScore:
    symbol: str
    score: float  # -1.0 (bearish) to 1.0 (bullish)
    summary: str = ""
    sources: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Position:
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    amount: float
    current_price: float = 0.0
    stop_loss: float | None = None
    take_profit: float | None = None
    opened_at: float = field(default_factory=lambda: datetime.now().timestamp())

    @property
    def unrealized_pnl_pct(self) -> float:
        if not self.current_price or not self.entry_price:
            return 0.0
        if self.side == "long":
            return (self.current_price - self.entry_price) / self.entry_price * 100
        return (self.entry_price - self.current_price) / self.entry_price * 100

    @property
    def unrealized_pnl(self) -> float:
        return self.amount * self.entry_price * self.unrealized_pnl_pct / 100


@dataclass
class Balance:
    total_usd: float = 0.0
    available_usd: float = 0.0
    reserved_usd: float = 0.0
    assets: dict[str, float] = field(default_factory=dict)  # {symbol: amount}


@dataclass
class Decision:
    action: Action
    symbol: str
    amount_pct: float = 0.0
    confidence: int = 0
    reasoning: str = ""
    indicators_used: list[str] = field(default_factory=list)
    news_factors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    price: float | None = None  # None for market orders
    stop_loss: float | None = None
    take_profit: float | None = None


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    type: str
    amount: float
    price: float
    status: str  # "filled", "partial", "cancelled", "error"
    fee: float = 0.0
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    error: str = ""


@dataclass
class MarketContext:
    """Full context passed to strategy.analyze()."""
    symbol: str
    timeframe: str
    candles: list[Candle]
    ticker: Ticker
    indicators: Indicators
    orderbook: OrderBook | None = None
    sentiment: SentimentScore | None = None
    balance: Balance | None = None
    positions: list[Position] = field(default_factory=list)
    daily_pnl_pct: float = 0.0
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """Notification event passed to notifier.send()."""
    category: str  # "trade", "stop_loss", "daily_report", "error", "kill_switch"
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Report:
    """Summary report passed to notifier.send_report()."""
    report_type: str  # "daily", "weekly", "monthly"
    total_pnl: float
    total_pnl_pct: float
    trades_count: int
    win_rate: float
    open_positions: list[Position]
    balance: Balance
    period_start: float
    period_end: float
    metadata: dict[str, Any] = field(default_factory=dict)
