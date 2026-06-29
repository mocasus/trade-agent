"""Rule-based strategy plugin."""
from __future__ import annotations

import logging
from typing import Any

from trade_agent.interfaces import StrategyInterface
from trade_agent.models import Action, Decision, MarketContext

logger = logging.getLogger("trade-agent.strategy.rule")


class RuleStrategy(StrategyInterface):
    def __init__(self):
        self._rules: list[dict] = []

    def init(self, config: dict[str, Any]) -> None:
        self._rules = config.get("rules", [])

    def analyze(self, context: MarketContext) -> Decision:
        ind = context.indicators
        ind_dict = ind.to_dict() if ind else {}

        for rule in self._rules:
            condition = rule.get("condition", "")
            try:
                if self._eval_condition(condition, ind_dict):
                    return Decision(
                        action=Action(rule.get("action", "HOLD")),
                        symbol=context.symbol,
                        amount_pct=float(rule.get("amount_pct", 5)),
                        confidence=int(rule.get("confidence", 70)),
                        reasoning=f"Rule '{rule.get('name', condition)}' triggered",
                        indicators_used=list(ind_dict.keys()),
                    )
            except Exception:
                logger.debug("Rule condition error: %s", condition)

        return Decision(action=Action.HOLD, symbol=context.symbol, confidence=50, reasoning="No rules matched")

    def _eval_condition(self, condition: str, ind: dict[str, float]) -> bool:
        """Evaluate simple conditions like 'rsi < 30', 'macd > 0'."""
        condition = condition.strip()
        for op in ["<=", ">=", "==", "!=", "<", ">"]:
            if op in condition:
                parts = condition.split(op)
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                val_str = parts[1].strip()
                if key not in ind:
                    return False
                val = float(val_str)
                actual = float(ind[key])
                if op == "<":
                    return actual < val
                elif op == ">":
                    return actual > val
                elif op == "<=":
                    return actual <= val
                elif op == ">=":
                    return actual >= val
                elif op == "==":
                    return abs(actual - val) < 1e-6
                elif op == "!=":
                    return abs(actual - val) > 1e-6
        return False

    def shutdown(self) -> None:
        pass


def register():
    return {"name": "rule", "class": RuleStrategy, "description": "Rule-based strategy (config conditions)"}
