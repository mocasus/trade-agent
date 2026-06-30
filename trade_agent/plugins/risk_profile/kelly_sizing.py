"""Kelly criterion position sizing."""

from __future__ import annotations
from trade_agent.interfaces import RiskProfileInterface
from trade_agent.models import Decision, MarketContext, Position


class KellyCriterionProfile(RiskProfileInterface):
    def __init__(
        self,
        fraction: float = 0.5,
        min_samples: int = 10,
        default_win_rate: float = 0.55,
        default_win_loss_ratio: float = 1.5,
    ):
        self.fraction = fraction
        self.min_samples = min_samples
        self.default_win_rate = default_win_rate
        self.default_win_loss_ratio = default_win_loss_ratio
        self._wins = 0
        self._losses = 0
        self._total_win = 0.0
        self._total_loss = 0.0

    def _win_rate(self) -> float:
        total = self._wins + self._losses
        return self.default_win_rate if total < self.min_samples else self._wins / total

    def _win_loss_ratio(self) -> float:
        if self._losses == 0 or self._total_loss == 0:
            return self.default_win_loss_ratio
        avg_win = self._total_win / self._wins if self._wins else 0
        avg_loss = self._total_loss / self._losses if self._losses else 0
        return avg_win / avg_loss if avg_loss > 0 else self.default_win_loss_ratio

    def calculate_position_size(
        self, balance: float, price: float, confidence: float
    ) -> float:
        p = self._win_rate()
        b = self._win_loss_ratio()
        kelly = max(0, (b * p - (1 - p)) / b)
        sized = self.fraction * kelly * confidence
        return balance * min(sized, 0.25) / price

    def check_risk(
        self, decision: Decision, context: MarketContext, positions: list[Position]
    ) -> Decision:
        return decision

    def calculate_stop_loss(self, entry_price: float, atr: float = 0) -> float:
        return entry_price - 2 * atr if atr > 0 else entry_price * 0.95

    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        return entry_price + (entry_price - stop_loss) * 2

    def check_risk_rules(
        self, positions: list[Position], decision: Decision, daily_pnl_pct: float
    ) -> bool:
        if daily_pnl_pct < -5.0:
            return False
        return True

    def record_trade(self, pnl: float) -> None:
        if pnl > 0:
            self._wins += 1
            self._total_win += pnl
        elif pnl < 0:
            self._losses += 1
            self._total_loss += abs(pnl)
