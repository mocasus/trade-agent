"""Test the invinoveritas risk-profile plugin (optional pre-trade verification wrapper)."""

from unittest.mock import MagicMock, patch

from trade_agent.models import Action, Decision
from trade_agent.plugins.risk_profile.invinoveritas import InvinoveritasProfile


def _resp(status_code=200, json_body=None):
    m = MagicMock()
    m.status_code = status_code
    m.json.return_value = json_body or {}
    return m


def test_no_api_key_fails_open():
    p = InvinoveritasProfile()
    p.init({})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=80)
    with patch("trade_agent.plugins.risk_profile.invinoveritas.httpx.post") as mock_post:
        assert p.check_risk_rules([], d, 0.0) is True
        mock_post.assert_not_called()


def test_base_profile_veto_short_circuits_before_any_http_call():
    p = InvinoveritasProfile()
    # confidence 50 < moderate's confidence_floor (65) -> base profile itself says no
    p.init({"invinoveritas": {"api_key": "test-key"}})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=50)
    with patch("trade_agent.plugins.risk_profile.invinoveritas.httpx.post") as mock_post:
        assert p.check_risk_rules([], d, 0.0) is False
        mock_post.assert_not_called()


def test_reject_verdict_advisory_by_default_does_not_block():
    p = InvinoveritasProfile()
    p.init({"invinoveritas": {"api_key": "test-key"}})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=80)
    with patch("trade_agent.plugins.risk_profile.invinoveritas.httpx.post") as mock_post:
        mock_post.return_value = _resp(200, {"verdict": "reject", "summary": "too risky"})
        assert p.check_risk_rules([], d, 0.0) is True


def test_reject_verdict_blocks_when_enforce_true():
    p = InvinoveritasProfile()
    p.init({"invinoveritas": {"api_key": "test-key", "enforce": True}})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=80)
    with patch("trade_agent.plugins.risk_profile.invinoveritas.httpx.post") as mock_post:
        mock_post.return_value = _resp(200, {"verdict": "reject", "summary": "too risky"})
        assert p.check_risk_rules([], d, 0.0) is False


def test_approve_with_concerns_allows_trade():
    p = InvinoveritasProfile()
    p.init({"invinoveritas": {"api_key": "test-key", "enforce": True}})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=80)
    with patch("trade_agent.plugins.risk_profile.invinoveritas.httpx.post") as mock_post:
        mock_post.return_value = _resp(200, {"verdict": "approve_with_concerns", "summary": "ok-ish"})
        assert p.check_risk_rules([], d, 0.0) is True


def test_network_error_fails_open():
    import httpx as httpx_module

    p = InvinoveritasProfile()
    p.init({"invinoveritas": {"api_key": "test-key", "enforce": True}})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=80)
    with patch("trade_agent.plugins.risk_profile.invinoveritas.httpx.post") as mock_post:
        mock_post.side_effect = httpx_module.ConnectTimeout("timed out")
        assert p.check_risk_rules([], d, 0.0) is True


def test_payment_required_fails_open():
    p = InvinoveritasProfile()
    p.init({"invinoveritas": {"api_key": "test-key", "enforce": True}})
    d = Decision(action=Action.BUY, symbol="BTC", confidence=80)
    with patch("trade_agent.plugins.risk_profile.invinoveritas.httpx.post") as mock_post:
        mock_post.return_value = _resp(402, {})
        assert p.check_risk_rules([], d, 0.0) is True


def test_hold_never_calls_review():
    p = InvinoveritasProfile()
    p.init({"invinoveritas": {"api_key": "test-key"}})
    d = Decision(action=Action.HOLD, symbol="BTC", confidence=10)
    with patch("trade_agent.plugins.risk_profile.invinoveritas.httpx.post") as mock_post:
        assert p.check_risk_rules([], d, 0.0) is True
        mock_post.assert_not_called()


def test_position_sizing_delegates_to_base_profile():
    p = InvinoveritasProfile()
    p.init({"base_profile": "conservative"})
    from trade_agent.plugins.risk_profile.conservative import ConservativeProfile

    ref = ConservativeProfile()
    ref.init({})
    assert p.calculate_position_size(10000, 80) == ref.calculate_position_size(10000, 80)


def test_plugin_registers():
    from trade_agent.plugins.risk_profile.invinoveritas import register

    info = register()
    assert info["name"] == "invinoveritas"
    assert info["class"] is InvinoveritasProfile
