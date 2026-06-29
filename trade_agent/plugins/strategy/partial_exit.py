"""Partial exit strategy — scale out in increments."""
from __future__ import annotations
from trade_agent.interfaces import StrategyInterface
from trade_agent.models import Action, Candle, Decision, MarketContext, SentimentScore

class PartialExitStrategy(StrategyInterface):
    """Exit positions in stages: 25% at +5%, 25% at +10%, rest rides."""

    def __init__(self, levels: list[dict] | None = None):
        self.levels = levels or [
            {"pct_gain": 5.0, "exit_pct": 25},
            {"pct_gain": 10.0, "exit_pct": 25},
            {"pct_gain": 15.0, "exit_pct": 50},
        ]
        self._triggered: dict[str, set[int]] = {}

    def analyze(self, candles: list[Candle], context: MarketContext,
                sentiment: SentimentScore | None = None) -> Decision:
        if not context.ticker or not context.positions:
            return Decision(action=Action.HOLD, symbol="", confidence=0)

        symbol = context.positions[0].symbol
        entry = context.positions[0].entry_price
        current = context.ticker.last_price
        gain_pct = (current - entry) / entry * 100
        triggered = self._triggered.setdefault(symbol, set())

        for i, level in enumerate(self.levels):
            if i in triggered:
                continue
            if gain_pct >= level["pct_gain"]:
                triggered.add(i)
                return Decision(
                    action=Action.SELL,
                    symbol=symbol,
                    amount_pct=level["exit_pct"] / 100,
                    confidence=80,
                    reasoning=f"Partial exit: {level['exit_pct']}% at +{level['pct_gain']}% gain (current +{gain_pct:.1f}%)",
                )
        return Decision(action=Action.HOLD, symbol=symbol, confidence=30,
                        reasoning=f"Gain {gain_pct:.1f}% — no exit level triggered")
