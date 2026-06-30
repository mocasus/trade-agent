"""Tests for Phase 4 features."""

from trade_agent.plugins.strategy.rule_builder import RuleBuilderStrategy
from trade_agent.models import Action, Candle, Indicators, MarketContext, Ticker


def _ticker(price=100.0):
    return Ticker(
        symbol="BTC",
        last_price=price,
        bid=price - 0.1,
        ask=price + 0.1,
        volume_24h=1000,
        change_pct_24h=0,
    )


def _ctx(price=100.0):
    candles = [Candle(1, 100, 101, 99, 100, 100), Candle(2, 100, 102, 98, 101, 100)]
    return MarketContext(
        symbol="BTC",
        timeframe="1h",
        candles=candles,
        ticker=_ticker(price),
        indicators=Indicators(),
    )


def test_rule_builder_price_above():
    rules = [
        {
            "signal": "test",
            "condition": "price_above",
            "threshold": 100,
            "action": "sell",
            "confidence_weight": 0.7,
        }
    ]
    rb = RuleBuilderStrategy(rules=rules)
    dec = rb.analyze([], _ctx(105))
    assert dec.action == Action.SELL and dec.confidence == 70


def test_rule_builder_no_trigger():
    rules = [
        {
            "signal": "test",
            "condition": "price_above",
            "threshold": 200,
            "action": "sell",
            "confidence_weight": 0.7,
        }
    ]
    rb = RuleBuilderStrategy(rules=rules)
    dec = rb.analyze([], _ctx(105))
    assert dec.action == Action.HOLD


def test_rule_builder_multiple():
    rules = [
        {
            "signal": "rsi_low",
            "condition": "rsi_below",
            "threshold": 30,
            "action": "buy",
            "confidence_weight": 0.6,
        },
        {
            "signal": "price_low",
            "condition": "price_below",
            "threshold": 100,
            "action": "buy",
            "confidence_weight": 0.4,
        },
    ]
    rb = RuleBuilderStrategy(rules=rules)
    dec = rb.analyze([], _ctx(90))
    assert dec.action == Action.BUY
