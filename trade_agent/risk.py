"""Built-in risk profile implementations."""

from __future__ import annotations

from .interfaces import RiskProfileInterface
from .models import Decision, MarketContext, Position


class ConservativeProfile(RiskProfileInterface):
    """Conservative risk: small positions, tight stops, low confidence threshold."""

    def __init__(self):
        self.max_pct: float = 2.0
        self.min_pct: float = 0.5
        self.confidence_floor: int = 70
        self.stop_loss_pct: float = 1.5
        self.atr_multiplier: float = 1.0
        self.rr_ratio: float = 1.5
        self.max_loss_pct: float = 2.0
        self.max_trades: int = 10
        self.max_positions: int = 3
        self.max_consecutive_losses: int = 2
        self.reserve_pct: float = 20.0

    def init(self, config: dict) -> None:
        ps = config.get("position_sizing", {})
        self.max_pct = ps.get("max_pct", self.max_pct)
        self.min_pct = ps.get("min_pct", self.min_pct)
        sl = config.get("stop_loss", {})
        self.stop_loss_pct = sl.get("fixed_pct", self.stop_loss_pct)
        self.atr_multiplier = sl.get("atr_multiplier", self.atr_multiplier)
        tp = config.get("take_profit", {})
        self.rr_ratio = tp.get("rr_ratio", self.rr_ratio)
        dl = config.get("daily_limits", {})
        self.max_loss_pct = dl.get("max_loss_pct", self.max_loss_pct)
        self.max_trades = dl.get("max_trades", self.max_trades)
        self.max_positions = dl.get("max_open_positions", self.max_positions)
        self.max_consecutive_losses = dl.get(
            "max_consecutive_losses", self.max_consecutive_losses
        )
        self.reserve_pct = config.get("portfolio", {}).get(
            "reserve_pct", self.reserve_pct
        )

    def calculate_position_size(
        self, available_capital: float, confidence: int
    ) -> float:
        tradable = available_capital * (1 - self.reserve_pct / 100)
        pct = self.min_pct + (self.max_pct - self.min_pct) * (confidence / 100)
        pct = min(pct, self.max_pct)
        return tradable * pct / 100

    def calculate_stop_loss(self, entry_price: float, context: MarketContext) -> float:
        atr = context.indicators.atr
        if atr and atr > 0:
            return entry_price - atr * self.atr_multiplier
        return entry_price * (1 - self.stop_loss_pct / 100)

    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        risk = entry_price - stop_loss
        return entry_price + risk * self.rr_ratio

    def check_risk_rules(
        self, positions: list[Position], decision: Decision, daily_pnl_pct: float
    ) -> bool:
        if decision.action.value in ("HOLD",):
            return True
        if decision.confidence < self.confidence_floor:
            return False
        if daily_pnl_pct <= -self.max_loss_pct:
            return False
        if len(positions) >= self.max_positions and decision.action.value in ("BUY",):
            return False
        return True


class ModerateProfile(RiskProfileInterface):
    """Moderate risk: standard positions, moderate stops."""

    def __init__(self):
        self.max_pct: float = 8.0
        self.min_pct: float = 1.0
        self.confidence_floor: int = 65
        self.stop_loss_pct: float = 2.0
        self.atr_multiplier: float = 1.5
        self.rr_ratio: float = 2.0
        self.max_loss_pct: float = 5.0
        self.max_trades: int = 20
        self.max_positions: int = 5
        self.max_consecutive_losses: int = 3
        self.reserve_pct: float = 10.0

    def init(self, config: dict) -> None:
        ps = config.get("position_sizing", {})
        self.max_pct = ps.get("max_pct", self.max_pct)
        self.min_pct = ps.get("min_pct", self.min_pct)
        sl = config.get("stop_loss", {})
        self.stop_loss_pct = sl.get("fixed_pct", self.stop_loss_pct)
        self.atr_multiplier = sl.get("atr_multiplier", self.atr_multiplier)
        tp = config.get("take_profit", {})
        self.rr_ratio = tp.get("rr_ratio", self.rr_ratio)
        dl = config.get("daily_limits", {})
        self.max_loss_pct = dl.get("max_loss_pct", self.max_loss_pct)
        self.max_trades = dl.get("max_trades", self.max_trades)
        self.max_positions = dl.get("max_open_positions", self.max_positions)
        self.max_consecutive_losses = dl.get(
            "max_consecutive_losses", self.max_consecutive_losses
        )
        self.reserve_pct = config.get("portfolio", {}).get(
            "reserve_pct", self.reserve_pct
        )

    def calculate_position_size(
        self, available_capital: float, confidence: int
    ) -> float:
        tradable = available_capital * (1 - self.reserve_pct / 100)
        pct = self.min_pct + (self.max_pct - self.min_pct) * (confidence / 100)
        pct = min(pct, self.max_pct)
        return tradable * pct / 100

    def calculate_stop_loss(self, entry_price: float, context: MarketContext) -> float:
        atr = context.indicators.atr
        if atr and atr > 0:
            return entry_price - atr * self.atr_multiplier
        return entry_price * (1 - self.stop_loss_pct / 100)

    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        risk = entry_price - stop_loss
        return entry_price + risk * self.rr_ratio

    def check_risk_rules(
        self, positions: list[Position], decision: Decision, daily_pnl_pct: float
    ) -> bool:
        if decision.action.value in ("HOLD",):
            return True
        if decision.confidence < self.confidence_floor:
            return False
        if daily_pnl_pct <= -self.max_loss_pct:
            return False
        if len(positions) >= self.max_positions and decision.action.value in ("BUY",):
            return False
        return True


class AggressiveProfile(RiskProfileInterface):
    """Aggressive risk: large positions, loose stops."""

    def __init__(self):
        self.max_pct: float = 15.0
        self.min_pct: float = 2.0
        self.confidence_floor: int = 55
        self.stop_loss_pct: float = 3.5
        self.atr_multiplier: float = 2.0
        self.rr_ratio: float = 1.5
        self.max_loss_pct: float = 10.0
        self.max_trades: int = 30
        self.max_positions: int = 8
        self.max_consecutive_losses: int = 5
        self.reserve_pct: float = 5.0

    def init(self, config: dict) -> None:
        ps = config.get("position_sizing", {})
        self.max_pct = ps.get("max_pct", self.max_pct)
        self.min_pct = ps.get("min_pct", self.min_pct)
        sl = config.get("stop_loss", {})
        self.stop_loss_pct = sl.get("fixed_pct", self.stop_loss_pct)
        self.atr_multiplier = sl.get("atr_multiplier", self.atr_multiplier)
        tp = config.get("take_profit", {})
        self.rr_ratio = tp.get("rr_ratio", self.rr_ratio)
        dl = config.get("daily_limits", {})
        self.max_loss_pct = dl.get("max_loss_pct", self.max_loss_pct)
        self.max_trades = dl.get("max_trades", self.max_trades)
        self.max_positions = dl.get("max_open_positions", self.max_positions)
        self.max_consecutive_losses = dl.get(
            "max_consecutive_losses", self.max_consecutive_losses
        )
        self.reserve_pct = config.get("portfolio", {}).get(
            "reserve_pct", self.reserve_pct
        )

    def calculate_position_size(
        self, available_capital: float, confidence: int
    ) -> float:
        tradable = available_capital * (1 - self.reserve_pct / 100)
        pct = self.min_pct + (self.max_pct - self.min_pct) * (confidence / 100)
        pct = min(pct, self.max_pct)
        return tradable * pct / 100

    def calculate_stop_loss(self, entry_price: float, context: MarketContext) -> float:
        atr = context.indicators.atr
        if atr and atr > 0:
            return entry_price - atr * self.atr_multiplier
        return entry_price * (1 - self.stop_loss_pct / 100)

    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        risk = entry_price - stop_loss
        return entry_price + risk * self.rr_ratio

    def check_risk_rules(
        self, positions: list[Position], decision: Decision, daily_pnl_pct: float
    ) -> bool:
        if decision.action.value in ("HOLD",):
            return True
        if decision.confidence < self.confidence_floor:
            return False
        if daily_pnl_pct <= -self.max_loss_pct:
            return False
        if len(positions) >= self.max_positions and decision.action.value in ("BUY",):
            return False
        return True


def register():
    return {
        "conservative": {
            "name": "conservative",
            "class": ConservativeProfile,
            "description": "Conservative risk: small positions, tight stops",
        },
        "moderate": {
            "name": "moderate",
            "class": ModerateProfile,
            "description": "Moderate risk: standard positions, moderate stops",
        },
        "aggressive": {
            "name": "aggressive",
            "class": AggressiveProfile,
            "description": "Aggressive risk: large positions, loose stops",
        },
    }
