"""Trailing stop-loss risk profile."""
from __future__ import annotations
from trade_agent.interfaces import RiskProfileInterface
from trade_agent.models import Action, Decision, MarketContext, Position

class TrailingStopProfile(RiskProfileInterface):
    """Trailing stop that moves up with price, never down."""

    def __init__(self, trail_percent: float = 2.0, activation_threshold: float = 1.0):
        self.trail_percent = trail_percent
        self.activation_threshold = activation_threshold
        self._highest_price: dict[str, float] = {}

    def calculate_position_size(self, balance: float, price: float, confidence: float) -> float:
        max_pct = 0.05 * confidence
        return balance * max_pct / price

    def check_risk(self, decision: Decision, context: MarketContext, positions: list[Position]) -> Decision:
        symbol = decision.symbol
        current_price = context.ticker.last_price if context.ticker else 0
        entry_price = positions[0].entry_price if positions else current_price

        if symbol not in self._highest_price:
            self._highest_price[symbol] = current_price
        self._highest_price[symbol] = max(self._highest_price[symbol], current_price)

        profit_pct = (current_price - entry_price) / entry_price * 100
        if profit_pct < self.activation_threshold:
            return decision

        highest = self._highest_price[symbol]
        trail_stop = highest * (1 - self.trail_percent / 100)

        if current_price <= trail_stop:
            return Decision(
                action=Action.SELL,
                symbol=symbol,
                confidence=int(decision.confidence * 0.9),
                reasoning=f"Trailing stop hit: {current_price:.2f} <= {trail_stop:.2f} (high={highest:.2f})",
            )
        return decision

    def calculate_stop_loss(self, entry_price: float, atr: float = 0) -> float:
        return entry_price * (1 - self.trail_percent / 100)

    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        return entry_price + (entry_price - stop_loss) * 2

    def check_risk_rules(self, positions: list[Position], decision: Decision, daily_pnl_pct: float) -> bool:
        if daily_pnl_pct < -5.0:
            return False
        return True
