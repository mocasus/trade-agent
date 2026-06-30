"""Moderate risk profile plugin."""

from trade_agent.interfaces import RiskProfileInterface
from trade_agent.models import MarketContext


class ModerateProfile(RiskProfileInterface):
    def __init__(self):
        self.max_pct = 8.0
        self.min_pct = 1.0
        self.confidence_floor = 65
        self.stop_loss_pct = 2.0
        self.atr_multiplier = 1.5
        self.rr_ratio = 2.0
        self.max_loss_pct = 5.0
        self.max_positions = 5
        self.reserve_pct = 10.0

    def init(self, config) -> None:
        ps = config.get("position_sizing", {})
        self.max_pct = ps.get("max_pct", self.max_pct)
        self.min_pct = ps.get("min_pct", self.min_pct)
        sl = config.get("stop_loss", {})
        self.atr_multiplier = sl.get("atr_multiplier", self.atr_multiplier)
        self.stop_loss_pct = sl.get("fixed_pct", self.stop_loss_pct)
        tp = config.get("take_profit", {})
        self.rr_ratio = tp.get("rr_ratio", self.rr_ratio)
        dl = config.get("daily_limits", {})
        self.max_loss_pct = dl.get("max_loss_pct", self.max_loss_pct)
        self.max_positions = dl.get("max_open_positions", self.max_positions)
        self.reserve_pct = config.get("portfolio", {}).get(
            "reserve_pct", self.reserve_pct
        )

    def calculate_position_size(
        self, available_capital: float, confidence: int
    ) -> float:
        tradable = available_capital * (1 - self.reserve_pct / 100)
        pct = self.min_pct + (self.max_pct - self.min_pct) * min(confidence / 100, 1)
        return tradable * min(pct, self.max_pct) / 100

    def calculate_stop_loss(self, entry_price: float, context: MarketContext) -> float:
        atr = context.indicators.atr if context.indicators else None
        if atr and atr > 0:
            return entry_price - atr * self.atr_multiplier
        return entry_price * (1 - self.stop_loss_pct / 100)

    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        return entry_price + (entry_price - stop_loss) * self.rr_ratio

    def check_risk_rules(self, positions, decision, daily_pnl_pct) -> bool:
        if decision.action.value == "HOLD":
            return True
        if decision.confidence < self.confidence_floor:
            return False
        if daily_pnl_pct <= -self.max_loss_pct:
            return False
        if len(positions) >= self.max_positions and decision.action.value == "BUY":
            return False
        return True


def register():
    return {
        "name": "moderate",
        "class": ModerateProfile,
        "description": "Moderate risk profile",
    }
