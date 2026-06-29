"""Plugin discovery, registration, and loading system."""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from .interfaces import (
    DataSourceInterface,
    ExchangeInterface,
    IndicatorPluginInterface,
    NotifierInterface,
    RiskProfileInterface,
    SentimentInterface,
    StrategyInterface,
)

_INTERFACE_MAP = {
    "data_source": DataSourceInterface,
    "strategy": StrategyInterface,
    "exchange": ExchangeInterface,
    "notifier": NotifierInterface,
    "sentiment": SentimentInterface,
    "risk_profile": RiskProfileInterface,
    "indicators": IndicatorPluginInterface,
}


def _discover_in_dir(base_dir: Path, slot: str) -> dict[str, type]:
    """Find plugins implementing the given interface in a directory."""
    result: dict[str, type] = {}
    slot_dir = base_dir / slot
    if not slot_dir.is_dir():
        return result

    for py in sorted(slot_dir.glob("*.py")):
        if py.name.startswith("_"):
            continue
        mod_name = f"_ta_plugin_{slot}_{py.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, py)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            continue
        if hasattr(mod, "register"):
            info = mod.register()
            name = info.get("name", py.stem)
            cls = info.get("class")
            if cls:
                result[name] = cls
    return result


class PluginLoader:
    """Discovers and instantiates plugins from built-in and user directories."""

    def __init__(self, builtin_dir: Path, user_dir: Path | None = None):
        self._builtin = builtin_dir
        self._user = user_dir or Path("~/.trade-agent/plugins").expanduser()
        self._cache: dict[str, dict[str, type]] = {}

    def _discover(self, slot: str) -> dict[str, type]:
        """Discover all plugins for a slot (built-in + user)."""
        if slot in self._cache:
            return self._cache[slot]

        plugins: dict[str, type] = {}
        # Built-in first, user overrides
        plugins.update(_discover_in_dir(self._builtin, slot))
        plugins.update(_discover_in_dir(self._user, slot))
        self._cache[slot] = plugins
        return plugins

    def get_available(self, slot: str) -> list[str]:
        """Return list of available plugin names for a slot."""
        return sorted(self._discover(slot).keys())

    def load(self, slot: str, name: str, config: dict[str, Any] | None = None) -> Any:
        """Load and initialize a single plugin instance.

        Args:
            slot: Plugin slot name (e.g., "strategy", "exchange").
            name: Plugin name (e.g., "llm", "ccxt").
            config: Config dict passed to plugin.init().

        Returns:
            Initialized plugin instance.
        """
        plugins = self._discover(slot)
        if name not in plugins:
            available = ", ".join(sorted(plugins.keys())) or "(none found)"
            raise ValueError(f"Plugin '{name}' not found for slot '{slot}'. Available: {available}")

        cls = plugins[name]
        interface = _INTERFACE_MAP.get(slot)
        if interface and not issubclass(cls, interface):
            raise TypeError(
                f"Plugin '{name}' ({cls.__name__}) does not implement {interface.__name__}"
            )

        instance = cls()
        if config:
            instance.init(config)
        return instance

    def load_many(self, slot: str, names: list[str], config: dict[str, Any] | None = None) -> list[Any]:
        """Load multiple plugin instances (for slots like 'notifier' that support multiple)."""
        return [self.load(slot, n, config) for n in names]

    def load_from_config(self, config: dict[str, Any], builtin_dir: Path | None = None) -> dict[str, Any]:
        """Load all plugins based on config['plugins'] section.

        Returns dict with keys: data_source, strategy, exchange,
        notifiers (list), sentiment, risk_profile, indicators.
        """
        plugins_cfg = config.get("plugins", {})
        bd = builtin_dir or self._builtin

        result: dict[str, Any] = {}

        # Single-instance slots
        for slot in ("data_source", "strategy", "exchange", "sentiment", "risk_profile", "indicators"):
            name = plugins_cfg.get(slot)
            if name:
                slot_config = config.get(slot, {})
                result[slot] = self.load(slot, name, slot_config)

        # Multi-instance: notifiers
        notifier_names = plugins_cfg.get("notifier", [])
        if isinstance(notifier_names, str):
            notifier_names = [notifier_names]
        notifiers_cfg = config.get("notifiers", {})
        result["notifiers"] = []
        for nname in notifier_names:
            ncfg = notifiers_cfg.get(nname, {})
            result["notifiers"].append(self.load("notifier", nname, ncfg))

        return result
