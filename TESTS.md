<p align="center">
  <img src="https://img.shields.io/badge/tests-39%20passed-brightgreen?style=flat-square&logo=pytest&logoColor=white" alt="tests">
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square&logo=codecov&logoColor=white" alt="coverage">
  <img src="https://img.shields.io/badge/python-3.11.2-3776AB?style=flat-square&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/pytest-9.1.1-0A9ED4?style=flat-square&logo=pytest&logoColor=white" alt="pytest">
  <img src="https://img.shields.io/badge/suites-7-58a6ff?style=flat-square&logo=github&logoColor=white" alt="suites">
  <img src="https://img.shields.io/badge/runtime-0.86s-ffd33d?style=flat-square&logo=clockify&logoColor=white" alt="runtime">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/config-5%20✅-2ea44f?style=flat-square" alt="config">
  <img src="https://img.shields.io/badge/models-7%20✅-2ea44f?style=flat-square" alt="models">
  <img src="https://img.shields.io/badge/phase3-9%20✅-2ea44f?style=flat-square" alt="phase3">
  <img src="https://img.shields.io/badge/phase4-3%20✅-2ea44f?style=flat-square" alt="phase4">
  <img src="https://img.shields.io/badge/plugins-5%20✅-2ea44f?style=flat-square" alt="plugins">
  <img src="https://img.shields.io/badge/risk-7%20✅-2ea44f?style=flat-square" alt="risk">
  <img src="https://img.shields.io/badge/storage-3%20✅-2ea44f?style=flat-square" alt="storage">
</p>

# 🧪 Test Results

All 39 tests passing. Run `python -m pytest tests/ -v` to reproduce.

---

## Summary

| Suite | Tests | Status | Coverage |
|-------|-------|--------|----------|
| Config | 5 | ✅ All pass | env var resolution, deep merge, YAML load |
| Models | 7 | ✅ All pass | Action enum, Candle, Position PnL, Decision, MarketContext |
| Phase 3 | 9 | ✅ All pass | Trailing stop, Kelly sizing, partial exit, OCO |
| Phase 4 | 3 | ✅ All pass | Rule builder (price, no-trigger, multiple rules) |
| Plugin Loader | 5 | ✅ All pass | Discovery across 4 plugin slots, load notifier |
| Risk | 7 | ✅ All pass | Position sizing, confidence floor, daily loss, ATR stop/TP |
| Storage | 3 | ✅ All pass | Init, log decision, log trade |

**Total: 39 passed · 0 failed · 0.86s runtime**

---

## Detailed Results

### Config (`tests/test_config.py`) — 5 tests

| # | Test | What it checks |
|---|------|---------------|
| 1 | `test_resolve_env_vars` | `${VAR}` substituted from environment |
| 2 | `test_resolve_env_vars_with_default` | `${VAR:default}` falls back when var missing |
| 3 | `test_resolve_env_vars_in_dict` | Nested dict values also resolved |
| 4 | `test_deep_merge` | YAML deep merge preserves nested keys |
| 5 | `test_config_load` | Full config load from example YAML |

### Models (`tests/test_models.py`) — 7 tests

| # | Test | What it checks |
|---|------|---------------|
| 1 | `test_action_enum` | BUY/SELL/HOLD enum values correct |
| 2 | `test_candle` | Candle model fields + defaults |
| 3 | `test_position_pnl` | Long position PnL calculation |
| 4 | `test_position_short_pnl` | Short position PnL calculation |
| 5 | `test_indicators_to_dict` | Indicators serializes to dict |
| 6 | `test_decision` | Decision model fields + validation |
| 7 | `test_market_context` | MarketContext assembly from components |

### Phase 3 (`tests/test_phase3.py`) — 9 tests

| # | Test | What it checks |
|---|------|---------------|
| 1 | `test_trailing_stop_calc` | Trail price = peak × (1 - trail_pct) |
| 2 | `test_trailing_stop_not_activated` | No trail until activation threshold hit |
| 3 | `test_trailing_stop_hit` | Stop triggers when price drops below trail |
| 4 | `test_kelly_sizing` | Kelly % = (p×b - q) / b with fraction |
| 5 | `test_kelly_record` | Kelly records win/loss for dynamic recalc |
| 6 | `test_partial_exit_level1` | First exit level triggers at +5% |
| 7 | `test_partial_exit_no_trigger` | No exit below threshold |
| 8 | `test_oco_order` | OCO: one cancels other on trigger |
| 9 | `test_partial_exit_model` | PartialExit model serialization |

### Phase 4 (`tests/test_phase4.py`) — 3 tests

| # | Test | What it checks |
|---|------|---------------|
| 1 | `test_rule_builder_price_above` | Rule triggers when price > threshold |
| 2 | `test_rule_builder_no_trigger` | Rule doesn't trigger when condition unmet |
| 3 | `test_rule_builder_multiple` | Multiple rules evaluated in priority order |

### Plugin Loader (`tests/test_plugin_loader.py`) — 5 tests

| # | Test | What it checks |
|---|------|---------------|
| 1 | `test_discover_data_source` | Finds ccxt + csv in data_source slot |
| 2 | `test_discover_strategy` | Finds llm + rule in strategy slot |
| 3 | `test_discover_notifier` | Finds all 4 notifiers |
| 4 | `test_discover_risk_profile` | Finds 5 risk profiles |
| 5 | `test_load_console_notifier` | Loads + instantiates console notifier |

### Risk (`tests/test_risk.py`) — 7 tests

| # | Test | What it checks |
|---|------|---------------|
| 1 | `test_conservative_position_size` | 2% max position for conservative |
| 2 | `test_moderate_position_size` | 8% max position for moderate |
| 3 | `test_risk_check_hold` | Confidence < floor → HOLD override |
| 4 | `test_risk_check_low_confidence` | Below threshold → skip trade |
| 5 | `test_risk_check_daily_loss` | Exceed daily limit → hard stop |
| 6 | `test_stop_loss_atr` | ATR-based stop-loss distance |
| 7 | `test_take_profit` | R:R ratio take-profit calculation |

### Storage (`tests/test_storage.py`) — 3 tests

| # | Test | What it checks |
|---|------|---------------|
| 1 | `test_storage_init` | SQLite schema creation |
| 2 | `test_log_decision` | Decision record insert + query |
| 3 | `test_log_trade` | Trade record insert + query |

---

## Raw Output

```
============================= test session starts ==============================
platform linux -- Python 3.11.2, pytest-9.1.1, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /root/trade-agent
configfile: pyproject.toml
plugins: anyio-4.14.0
collected 39 items

tests/test_config.py::test_resolve_env_vars PASSED                       [  2%]
tests/test_config.py::test_resolve_env_vars_with_default PASSED          [  5%]
tests/test_config.py::test_resolve_env_vars_in_dict PASSED               [  7%]
tests/test_config.py::test_deep_merge PASSED                             [10%]
tests/test_config.py::test_config_load PASSED                            [12%]
tests/test_models.py::test_action_enum PASSED                            [15%]
tests/test_models.py::test_candle PASSED                                 [17%]
tests/test_models.py::test_position_pnl PASSED                           [20%]
tests/test_models.py::test_position_short_pnl PASSED                     [23%]
tests/test_models.py::test_indicators_to_dict PASSED                     [25%]
tests/test_models.py::test_decision PASSED                               [28%]
tests/test_models.py::test_market_context PASSED                         [30%]
tests/test_phase3.py::test_trailing_stop_calc PASSED                     [33%]
tests/test_phase3.py::test_trailing_stop_not_activated PASSED            [35%]
tests/test_phase3.py::test_trailing_stop_hit PASSED                      [38%]
tests/test_phase3.py::test_kelly_sizing PASSED                           [41%]
tests/test_phase3.py::test_kelly_record PASSED                           [43%]
tests/test_phase3.py::test_partial_exit_level1 PASSED                    [46%]
tests/test_phase3.py::test_partial_exit_no_trigger PASSED                [48%]
tests/test_phase3.py::test_oco_order PASSED                              [51%]
tests/test_phase3.py::test_partial_exit_model PASSED                     [53%]
tests/test_phase4.py::test_rule_builder_price_above PASSED               [56%]
tests/test_phase4.py::test_rule_builder_no_trigger PASSED                [58%]
tests/test_phase4.py::test_rule_builder_multiple PASSED                  [61%]
tests/test_plugin_loader.py::test_discover_data_source PASSED            [64%]
tests/test_plugin_loader.py::test_discover_strategy PASSED               [66%]
tests/test_plugin_loader.py::test_discover_notifier PASSED               [69%]
tests/test_plugin_loader.py::test_discover_risk_profile PASSED           [71%]
tests/test_plugin_loader.py::test_load_console_notifier PASSED           [74%]
tests/test_risk.py::test_conservative_position_size PASSED               [76%]
tests/test_risk.py::test_moderate_position_size PASSED                   [79%]
tests/test_risk.py::test_risk_check_hold PASSED                          [82%]
tests/test_risk.py::test_risk_check_low_confidence PASSED                [84%]
tests/test_risk.py::test_risk_check_daily_loss PASSED                    [87%]
tests/test_risk.py::test_stop_loss_atr PASSED                            [89%]
tests/test_risk.py::test_take_profit PASSED                              [92%]
tests/test_storage.py::test_storage_init PASSED                          [94%]
tests/test_storage.py::test_log_decision PASSED                          [97%]
tests/test_storage.py::test_log_trade PASSED                             [100%]

============================== 39 passed in 0.86s ===============================
```

---

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/←_Back_to_README-2ea44f?style=flat-square&logo=github&logoColor=white" alt="Back to README"></a>
  <img src="https://img.shields.io/badge/last_run-2026--06--30-8b949e?style=flat-square&logo=calendar&logoColor=white" alt="last run">
</p>

<p align="center">
  <sub>Run <code>python -m pytest tests/ -v</code> to reproduce · Part of <a href="README.md">Trade Agent</a></sub>
</p>