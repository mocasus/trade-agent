"""Test SQLite storage."""
import tempfile
from pathlib import Path
from trade_agent.models import Action, Decision, OrderResult
from trade_agent.storage import Storage


def test_storage_init():
    with tempfile.TemporaryDirectory() as tmp:
        store = Storage(Path(tmp) / "test.db")
        store.init()
        assert store.conn is not None
        store.shutdown()


def test_log_decision():
    with tempfile.TemporaryDirectory() as tmp:
        store = Storage(Path(tmp) / "test.db")
        store.init()
        d = Decision(action=Action.BUY, symbol="BTCUSDT", confidence=80, reasoning="Test")
        rowid = store.log_decision(d, executed=True, order_id="ORDER123")
        assert rowid > 0
        decisions = store.get_decisions("BTCUSDT")
        assert len(decisions) == 1
        assert decisions[0]["action"] == "BUY"
        store.shutdown()


def test_log_trade():
    with tempfile.TemporaryDirectory() as tmp:
        store = Storage(Path(tmp) / "test.db")
        store.init()
        result = OrderResult(order_id="T1", symbol="BTCUSDT", side="buy", type="market",
                             amount=0.001, price=50000, fee=0.5, status="filled")
        rowid = store.log_trade(result, stop_loss=49000, take_profit=52000)
        assert rowid > 0
        trades = store.get_trades("BTCUSDT")
        assert len(trades) == 1
        assert trades[0]["stop_loss"] == 49000
        store.shutdown()
