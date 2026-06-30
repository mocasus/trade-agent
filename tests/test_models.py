"""Test data models."""

from trade_agent.models import (
    Action,
    Candle,
    Decision,
    Position,
    Ticker,
    Indicators,
    MarketContext,
)


def test_action_enum():
    assert Action.BUY.value == "BUY"
    assert Action.HOLD.value == "HOLD"


def test_candle():
    c = Candle(
        timestamp=1234567890, open=50000, high=50500, low=49500, close=50200, volume=100
    )
    assert c.close == 50200


def test_position_pnl():
    p = Position(
        symbol="BTC", side="long", entry_price=50000, amount=0.1, current_price=51000
    )
    assert p.unrealized_pnl_pct == 2.0
    assert p.unrealized_pnl == 100.0


def test_position_short_pnl():
    p = Position(
        symbol="BTC", side="short", entry_price=50000, amount=0.1, current_price=49000
    )
    assert p.unrealized_pnl_pct == 2.0


def test_indicators_to_dict():
    ind = Indicators(rsi=45.5, macd=0.5)
    d = ind.to_dict()
    assert d["rsi"] == 45.5
    assert "ema_20" not in d


def test_decision():
    d = Decision(
        action=Action.BUY, symbol="BTCUSDT", confidence=80, reasoning="Strong uptrend"
    )
    assert d.action == Action.BUY
    assert d.confidence == 80


def test_market_context():
    candles = [
        Candle(timestamp=i, open=100, high=110, low=90, close=105, volume=10)
        for i in range(5)
    ]
    ticker = Ticker(
        symbol="BTC",
        last_price=105,
        bid=104,
        ask=106,
        volume_24h=100,
        change_pct_24h=2.5,
    )
    ind = Indicators(rsi=55)
    ctx = MarketContext(
        symbol="BTC", timeframe="15m", candles=candles, ticker=ticker, indicators=ind
    )
    assert ctx.symbol == "BTC"
    assert len(ctx.candles) == 5
