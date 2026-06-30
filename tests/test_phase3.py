"""Tests for Phase 3 features."""

from trade_agent.plugins.risk_profile.trailing_stop import TrailingStopProfile
from trade_agent.plugins.risk_profile.kelly_sizing import KellyCriterionProfile
from trade_agent.plugins.strategy.partial_exit import PartialExitStrategy
from trade_agent.models import (
    Action,
    Decision,
    Indicators,
    MarketContext,
    OCOOrder,
    PartialExit,
    Position,
    Ticker,
)


def _ticker(price=100.0):
    return Ticker(
        symbol="BTC",
        last_price=price,
        bid=price - 0.1,
        ask=price + 0.1,
        volume_24h=1000,
        change_pct_24h=0,
    )


def _ctx(price=100.0, positions=None):
    return MarketContext(
        symbol="BTC",
        timeframe="1h",
        candles=[],
        ticker=_ticker(price),
        indicators=Indicators(),
        positions=positions or [],
    )


def _pos(entry=100.0, amount=1.0):
    return Position(
        symbol="BTC", side="long", entry_price=entry, amount=amount, current_price=entry
    )


def test_trailing_stop_calc():
    ts = TrailingStopProfile(trail_percent=2.0)
    assert ts.calculate_stop_loss(100.0) == 98.0


def test_trailing_stop_not_activated():
    ts = TrailingStopProfile(trail_percent=2.0, activation_threshold=5.0)
    dec = Decision(action=Action.BUY, symbol="BTC", confidence=80)
    result = ts.check_risk(dec, _ctx(101), [])
    assert result.action == Action.BUY


def test_trailing_stop_hit():
    ts = TrailingStopProfile(trail_percent=2.0, activation_threshold=1.0)
    ts._highest_price["BTC"] = 110.0
    pos = _pos(entry=100)
    dec = Decision(action=Action.HOLD, symbol="BTC", confidence=80)
    result = ts.check_risk(dec, _ctx(107.7, [pos]), [pos])
    assert result.action == Action.SELL


def test_kelly_sizing():
    k = KellyCriterionProfile(fraction=0.5, min_samples=10)
    assert k.calculate_position_size(10000, 100, 0.5) > 0


def test_kelly_record():
    k = KellyCriterionProfile()
    k.record_trade(100)
    k.record_trade(-50)
    assert k._wins == 1 and k._losses == 1


def test_partial_exit_level1():
    pe = PartialExitStrategy()
    pos = _pos(entry=100)
    dec = pe.analyze([], _ctx(105, [pos]))
    assert dec.action == Action.SELL and dec.amount_pct == 0.25


def test_partial_exit_no_trigger():
    pe = PartialExitStrategy()
    pos = _pos(entry=100)
    dec = pe.analyze([], _ctx(102, [pos]))
    assert dec.action == Action.HOLD


def test_oco_order():
    oco = OCOOrder(
        symbol="BTC", side="sell", quantity=1, stop_price=95, limit_price=110
    )
    assert oco.stop_price == 95


def test_partial_exit_model():
    pe = PartialExit(
        position_id="pos1", exit_percentage=25, exit_price=105, remaining_quantity=0.75
    )
    assert pe.exit_percentage == 25
