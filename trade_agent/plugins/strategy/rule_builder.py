"""Config-driven rule-based strategy builder."""

from __future__ import annotations
from trade_agent.interfaces import StrategyInterface
from trade_agent.models import Action, Candle, Decision, MarketContext, SentimentScore


class RuleBuilderStrategy(StrategyInterface):
    CONDITIONS = {
        "price_above": lambda c, t, v: t.last_price > v,
        "price_below": lambda c, t, v: t.last_price < v,
        "rsi_above": lambda c, t, v: _calc_rsi(c) > v,
        "rsi_below": lambda c, t, v: _calc_rsi(c) < v,
        "volume_above": lambda c, t, v: t.volume_24h > v,
    }

    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules or []

    def analyze(
        self,
        candles: list[Candle],
        context: MarketContext,
        sentiment: SentimentScore | None = None,
    ) -> Decision:
        candles = candles or context.candles
        if not context.ticker or not candles:
            return Decision(action=Action.HOLD, symbol="", confidence=0)

        total_conf = 0
        best_action = Action.HOLD
        best_reason = "No rules triggered"

        for rule in self.rules:
            condition = rule.get("condition", "")
            threshold = rule.get("threshold", 0)
            action_str = rule.get("action", "hold").upper()
            weight = rule.get("confidence_weight", 1.0)

            check_fn = self.CONDITIONS.get(condition)
            if check_fn and check_fn(candles, context.ticker, threshold):
                total_conf += weight
                best_action = Action.BUY if action_str == "BUY" else Action.SELL
                best_reason = f"Rule: {rule.get('signal', '')} {condition} {threshold}"

        return Decision(
            action=best_action,
            symbol=context.ticker.symbol,
            confidence=int(min(total_conf * 100, 100)),
            reasoning=best_reason,
        )


def _calc_rsi(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 50.0
    closes = [c.close for c in candles[-(period + 1) :]]
    gains = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))
