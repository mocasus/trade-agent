"""Test risk profiles."""
from trade_agent.models import Action, Decision, Candle, Ticker, Indicators, MarketContext
from trade_agent.plugins.risk_profile.conservative import ConservativeProfile
from trade_agent.plugins.risk_profile.moderate import ModerateProfile
from trade_agent.plugins.risk_profile.aggressive import AggressiveProfile


def test_conservative_position_size():
    p = ConservativeProfile()
    p.init({})
    size = p.calculate_position_size(10000, 80)
    assert 50 < size < 200


def test_moderate_position_size():
    p = ModerateProfile()
    p.init({})
    size = p.calculate_position_size(10000, 80)
    assert size > 0


def test_risk_check_hold():
    p = ModerateProfile()
    p.init({})
    d = Decision(action=Action.HOLD, symbol="BTC", confidence=30)
    assert p.check_risk_rules([], d, 0.0) is True


def test_risk_check_low_confidence():
    p = ConservativeProfile()
    p.init({})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=50)
    assert p.check_risk_rules([], d, 0.0) is False


def test_risk_check_daily_loss():
    p = ModerateProfile()
    p.init({})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=80)
    assert p.check_risk_rules([], d, -6.0) is False


def test_stop_loss_atr():
    p = ModerateProfile()
    p.init({})
    candles = [Candle(timestamp=i, open=100, high=105, low=95, close=100, volume=10) for i in range(20)]
    ticker = Ticker(symbol="BTC", last_price=100, bid=99, ask=101, volume_24h=100, change_pct_24h=0)
    ind = Indicators(atr=2.0)
    ctx = MarketContext(symbol="BTC", timeframe="15m", candles=candles, ticker=ticker, indicators=ind)
    sl = p.calculate_stop_loss(100.0, ctx)
    assert sl == 97.0


def test_take_profit():
    p = ModerateProfile()
    p.init({})
    tp = p.calculate_take_profit(100.0, 97.0)
    assert tp == 106.0
