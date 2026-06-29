"""Test plugin loader."""
from pathlib import Path
from trade_agent.plugin_loader import PluginLoader

BUILTIN = Path(__file__).parent.parent / "trade_agent" / "plugins"


def test_discover_data_source():
    loader = PluginLoader(BUILTIN)
    available = loader.get_available("data_source")
    assert "csv" in available
    # ccxt requires the ccxt package to be installed
    try:
        import ccxt
        assert "ccxt" in available
    except ImportError:
        pass  # ccxt not installed, skip that assertion


def test_discover_strategy():
    loader = PluginLoader(BUILTIN)
    available = loader.get_available("strategy")
    assert "llm" in available
    assert "rule" in available


def test_discover_notifier():
    loader = PluginLoader(BUILTIN)
    available = loader.get_available("notifier")
    assert "console" in available
    assert "telegram" in available
    assert "webhook" in available
    assert "discord" in available


def test_discover_risk_profile():
    loader = PluginLoader(BUILTIN)
    available = loader.get_available("risk_profile")
    assert "conservative" in available
    assert "moderate" in available
    assert "aggressive" in available


def test_load_console_notifier():
    loader = PluginLoader(BUILTIN)
    notifier = loader.load("notifier", "console", {"alerts": ["all"]})
    assert notifier is not None
