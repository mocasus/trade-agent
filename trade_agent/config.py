"""YAML config loader with env var resolution and validation."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_ENV_RE = re.compile(r"\$\{([^}]+)\}")

_DEFAULTS = {
    "agent": {
        "name": "trade-agent-v1",
        "log_level": "INFO",
        "timezone": "UTC",
        "data_dir": "~/.trade-agent",
    },
    "plugins": {
        "data_source": "ccxt",
        "strategy": "llm",
        "exchange": "ccxt",
        "notifier": ["console"],
        "sentiment": "none",
        "risk_profile": "moderate",
        "indicators": "ta",
    },
    "trading": {
        "paper_mode": True,
        "fee_pct": 0.1,
        "slippage_pct": 0.05,
    },
    "risk": {
        "position_sizing": {"method": "fixed_pct", "max_pct": 8, "min_pct": 1},
        "stop_loss": {"method": "atr", "atr_multiplier": 1.5, "fixed_pct": 2},
        "take_profit": {"method": "rr_ratio", "rr_ratio": 2},
        "daily_limits": {
            "max_loss_pct": 5,
            "max_trades": 20,
            "max_open_positions": 5,
            "cooldown_minutes": 30,
            "max_consecutive_losses": 3,
        },
        "portfolio": {"reserve_pct": 10},
    },
    "safety": {
        "paper_mode_required_first_run": True,
        "kill_switch_enabled": True,
        "auto_stop_on_error": True,
        "max_api_failures": 5,
    },
    "schedule": {
        "interval_minutes": 15,
        "backfill_on_start": True,
    },
    "storage": {
        "db_path": "~/.trade-agent/trade-agent.db",
    },
}


def resolve_env_vars(value: Any) -> Any:
    """Resolve ${VAR} references in string values from environment variables."""
    if isinstance(value, str):

        def _replace(m) -> str:
            var = m.group(1)
            # Support default syntax: ${VAR:-default}
            if ":-" in var:
                var_name, default = var.split(":-", 1)
                return os.environ.get(var_name, default) or ""
            env_val = os.environ.get(var, "")
            return env_val if env_val else ""

        return _ENV_RE.sub(_replace, value)
    elif isinstance(value, dict):
        return {k: resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_env_vars(item) for item in value]
    return value


def deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, preserving nested dicts."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def expand_path(path_str: str) -> Path:
    """Expand ~ and resolve to absolute path."""
    return Path(path_str).expanduser().resolve()


class Config:
    """Configuration manager: load YAML, resolve env vars, merge defaults."""

    def __init__(self, config_path: Path | str | None = None):
        self._raw: dict[str, Any] = {}
        self._data: dict[str, Any] = {}
        self._path: Path | None = None

        if config_path:
            self.load(config_path)

    def load(self, config_path: Path | str) -> None:
        """Load config from YAML file, resolve env vars, merge defaults."""
        path = Path(config_path).expanduser().resolve()
        self._path = path

        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        self._raw = raw
        resolved = resolve_env_vars(raw)
        self._data = deep_merge(_DEFAULTS, resolved)

        # Expand path fields
        if "agent" in self._data:
            if "data_dir" in self._data["agent"]:
                self._data["agent"]["data_dir"] = str(
                    expand_path(self._data["agent"]["data_dir"])
                )
            if "log_file" in self._data["agent"]:
                self._data["agent"]["log_file"] = str(
                    expand_path(self._data["agent"]["log_file"])
                )
        if "storage" in self._data:
            for key in ("db_path", "backup_dir"):
                if key in self._data["storage"]:
                    self._data["storage"][key] = str(
                        expand_path(self._data["storage"][key])
                    )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dotted key (e.g., 'trading.paper_mode')."""
        parts = key.split(".")
        node = self._data
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return default
        return node

    def section(self, name: str) -> dict[str, Any]:
        """Get an entire config section (e.g., 'trading', 'risk')."""
        return self._data.get(name, {})

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    @property
    def raw(self) -> dict[str, Any]:
        return self._raw

    def validate(self) -> list[str]:
        """Basic validation — returns list of issues (empty = valid)."""
        issues = []
        data = self._data

        # Check required sections
        if not data.get("plugins"):
            issues.append("Missing 'plugins' section")

        # Check trading symbols
        trading = data.get("trading", {})
        if not trading.get("symbols"):
            issues.append("Missing 'trading.symbols' — at least one symbol required")

        # Check exchange config when ccxt is selected
        if data.get("plugins", {}).get("data_source") == "ccxt":
            ds = data.get("data_source", {})
            if not ds.get("exchange"):
                issues.append("data_source.exchange required when using ccxt plugin")

        # Safety: paper mode must be True if no real API keys
        if not trading.get("paper_mode", True):
            ds = data.get("data_source", {})
            if not ds.get("api_key") or not ds.get("api_secret"):
                issues.append(
                    "Paper mode is OFF but no exchange API keys configured — dangerous!"
                )

        return issues
