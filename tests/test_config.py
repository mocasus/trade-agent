"""Test config loading and env var resolution."""
import os
import tempfile
from trade_agent.config import Config, resolve_env_vars, deep_merge


def test_resolve_env_vars():
    os.environ["TEST_KEY_123"] = "secret_value"
    assert resolve_env_vars("${TEST_KEY_123}") == "secret_value"
    del os.environ["TEST_KEY_123"]


def test_resolve_env_vars_with_default():
    assert resolve_env_vars("${NONEXISTENT_VAR:-default123}") == "default123"


def test_resolve_env_vars_in_dict():
    os.environ["TEST_DICT_KEY"] = "val"
    result = resolve_env_vars({"api_key": "${TEST_DICT_KEY}", "name": "static"})
    assert result["api_key"] == "val"
    assert result["name"] == "static"
    del os.environ["TEST_DICT_KEY"]


def test_deep_merge():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"d": 4, "e": 5}, "f": 6}
    merged = deep_merge(base, override)
    assert merged == {"a": 1, "b": {"c": 2, "d": 4, "e": 5}, "f": 6}


def test_config_load():
    yaml_content = """
agent:
  name: "test-agent"
  log_level: "DEBUG"
trading:
  paper_mode: true
  symbols:
    - symbol: "BTCUSDT"
      enabled: true
      timeframe: "5m"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    config = Config(path)
    assert config.get("agent.name") == "test-agent"
    assert config.get("agent.log_level") == "DEBUG"
    assert config.get("trading.paper_mode") is True
    os.unlink(path)
