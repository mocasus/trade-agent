![version](https://img.shields.io/badge/version-1.0.0-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.11+-3776AB) ![tests](https://img.shields.io/badge/tests-39%20passed-brightgreen)

# Trade Agent

Modular AI trading agent with plugin system. LLM analyzes market data, news sentiment, and technical indicators — then makes informed trading decisions across multiple exchanges.

Every component (data source, strategy, exchange, notifier, sentiment, risk) is swappable via plugins implementing abstract interfaces. No framework. No lock-in.

---

<details>
<summary>🇮🇩 Bahasa Indonesia</summary>

## Apa ini?

Bot trading AI modular dengan sistem plugin. LLM analisa data market + news + indikator teknikal → decision → eksekusi trade di multiple exchange.

Setiap komponen bisa diganti via plugin. Nggak ada framework, nggak ada lock-in.

## Status

**v1.0.0 — All 4 phases complete**

| Phase | Fitur |
|-------|-------|
| 1 MVP | Plugin system, 6 interfaces, built-in plugins |
| 2 | Discord notifier, TG commands, Dockerfile |
| 3 | Trailing stop, Kelly sizing, Bybit futures, OCO, partial exit |
| 4 | Dashboard web UI, rule builder, docker-compose |

## Quick Start

```bash
git clone https://github.com/mocasus/trade-agent.git
cd trade-agent
pip install -e ".[all]"

cp config.example.yaml config.yaml

# Set env vars
echo "AI_API_KEY=sk-xxx" >> .env
echo "BINANCE_API_KEY=xxx" >> .env
echo "BINANCE_API_SECRET=xxx" >> .env

# Run (paper mode default — aman!)
python -m trade_agent --config config.yaml
```

## Plugin System

6 slot yang bisa diganti:
- **data_source**: ccxt (100+ exchange) | csv (backtest)
- **strategy**: llm | rule | partial_exit | rule_builder
- **exchange**: ccxt | paper | bybit_futures
- **notifier**: telegram | discord | webhook | console
- **sentiment**: rss_llm | none
- **risk_profile**: conservative | moderate | aggressive | trailing_stop | kelly_sizing
- **indicators**: ta (RSI, MACD, EMA, BB, ATR)

Bikin plugin custom: implement interface → taruh di `~/.trade-agent/plugins/`

## Safety

- Paper mode ON default — nggak bakal trade real money
- Paper mode forced 24h pertama
- Kill switch: Telegram `/stop`
- Daily loss limit hard stop
- Audit trail: semua decision + reasoning di-log

</details>

---

## Status

**v1.0.0 — All 4 phases complete** · 49 files · 3,722 LOC · 39 tests ✅

| Phase | Features |
|-------|----------|
| 1 MVP | Plugin system, 6 abstract interfaces, 15 built-in plugins, SQLite storage, backtest engine |
| 2 | Discord notifier, Telegram interactive commands, Dockerfile, test suite |
| 3 | Trailing stop-loss, Kelly criterion sizing, Bybit futures adapter, OCO orders, partial exit strategy |
| 4 | Web dashboard (dark theme), rule builder strategy, docker-compose multi-instance |

## Quick Start

```bash
git clone https://github.com/mocasus/trade-agent.git
cd trade-agent
pip install -e ".[all]"

cp config.example.yaml config.yaml  # Edit before running

# Set env vars in .env
echo "AI_API_KEY=sk-xxx" >> .env
echo "BINANCE_API_KEY=xxx" >> .env

python -m trade_agent --config config.yaml  # Paper mode by default
```

## Architecture

```
Plugin Registry
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│DataSource│ │ Strategy │ │ Exchange │ │ Notifier │ │Sentiment │
│ Plugins  │ │ Plugins  │ │ Plugins  │ │ Plugins  │ │ Plugins  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
      │            │            │
      ▼            ▼            ▼
┌─────────┐  ┌──────────┐  ┌─────────┐
│Data Layer│─▶│ Strategy │─▶│Execution│
└─────────┘  └──────────┘  └─────────┘
                                 │
              ┌─────────┐       ▼
              │ Storage │  ┌─────────┐
              │ SQLite  │  │Notifier │
              └─────────┘  └─────────┘
```

Core loop only knows interfaces — never concrete implementations. Swap any plugin without touching core code.

## Plugin System

7 swappable slots, each behind an abstract interface:

| Slot | Interface | Built-in Plugins |
|------|-----------|-----------------|
| data_source | `DataSourceInterface` | ccxt, csv |
| strategy | `StrategyInterface` | llm, rule, partial_exit, rule_builder |
| exchange | `ExchangeInterface` | ccxt, paper, bybit_futures |
| notifier | `NotifierInterface` | telegram, discord, webhook, console |
| sentiment | `SentimentInterface` | rss_llm, none |
| risk_profile | `RiskProfileInterface` | conservative, moderate, aggressive, trailing_stop, kelly_sizing |
| indicators | `IndicatorPluginInterface` | ta (RSI, MACD, EMA, BB, ATR) |

**Custom plugin**: implement the interface → place in `~/.trade-agent/plugins/<slot>/`

```python
# ~/.trade-agent/plugins/strategy/my_quant.py
from trade_agent.interfaces import StrategyInterface
from trade_agent.models import Decision, MarketContext, Action

class MyQuantStrategy(StrategyInterface):
    def analyze(self, context: MarketContext) -> Decision:
        return Decision(action=Action.BUY, symbol=context.symbol, confidence=80, reasoning="...")

def register():
    return {"name": "my_quant", "class": MyQuantStrategy, "description": "Custom quant strategy"}
```

Then in config: `plugins.strategy: "my_quant"`

## Advanced Features (Phase 3+4)

### Trailing Stop-Loss
Stop-loss that follows price upward — never goes down once activated. Configurable activation threshold and trail percent.

```yaml
risk:
  method: trailing_stop
  trailing_stop:
    activation_threshold: 0.03  # Activate after 3% profit
    trail_percent: 0.015        # Trail 1.5% below peak
```

### Kelly Criterion Position Sizing
Optimal position sizing using fractional Kelly criterion. Dynamically adjusts based on win rate and average win/loss ratio.

```yaml
risk:
  position_sizing:
    method: kelly
    kelly_fraction: 0.5  # Half-Kelly (recommended)
```

### Bybit Futures
USDT perpetual contracts via ccxt adapter. Supports leverage configuration, margin mode, and hedge mode.

```yaml
plugins:
  exchange: bybit_futures
exchange:
  bybit_futures:
    leverage: 3
    margin_mode: cross
```

### OCO Orders
One-Cancels-Other: place stop-loss + take-profit simultaneously. When one triggers, the other auto-cancels.

### Partial Exit Strategy
Scaled exits at predefined profit levels. Exit 25% at +5%, 25% at +10%, remaining at +15%.

```yaml
plugins:
  strategy: partial_exit
strategy:
  partial_exit:
    levels:
      - profit_pct: 5
        exit_pct: 25
      - profit_pct: 10
        exit_pct: 25
      - profit_pct: 15
        exit_pct: 50
```

### Rule Builder Strategy
Config-only strategy — no code needed. Define rules in YAML with conditions and actions.

```yaml
plugins:
  strategy: rule_builder
strategy:
  rule_builder:
    rules:
      - name: "RSI oversold buy"
        conditions:
          - indicator: rsi
            operator: "<"
            value: 30
        action: buy
        confidence: 75
      - name: "MACD sell"
        conditions:
          - indicator: macd_histogram
            operator: "<"
            value: 0
        action: sell
        confidence: 70
```

### Web Dashboard
Dark-themed monitoring dashboard. View portfolio, positions, recent decisions, and PnL in real-time.

```bash
python -m trade_agent.dashboard --config config.yaml  # Starts on :8080
```

## Configuration

Deep YAML config with env var resolution. See `config.example.yaml` for all options.

Key settings:
- **Plugin selection**: swap any slot via `plugins` section
- **Per-symbol overrides**: different strategy/risk per symbol
- **Risk profiles**: position sizing method, stop-loss method, take-profit method
- **Custom prompts**: template file for LLM strategy
- **Per-notifier routing**: send only specific alert types to each notifier
- **Env vars**: `${API_KEY}` resolved from `.env`

## Risk Management

Five built-in profiles + custom via plugin:

| | Conservative | Moderate | Aggressive | Trailing Stop | Kelly |
|---|---|---|---|---|---|
| Max position | 2% | 8% | 15% | 10% | Dynamic |
| Confidence floor | 70 | 65 | 55 | 60 | 60 |
| Stop-loss | ATR×1.0 | ATR×1.5 | ATR×2.0 | Trail 1.5% | ATR×1.5 |
| R:R ratio | 1.5 | 2.0 | 1.5 | Variable | 2.0 |
| Daily loss limit | 2% | 5% | 10% | 5% | 5% |

All profiles respect config overrides. Position sizing: fixed %, Kelly criterion, or volatility-adjusted.

## Safety

- **Paper mode ON by default** — won't trade real money
- **Paper mode forced for first 24h** — can't accidentally go live
- **Kill switch** — Telegram `/stop` halts immediately
- **Daily loss limit** — hard stop, can't be overridden by AI
- **Max position size** — AI can't exceed configured %
- **Audit trail** — every decision logged with reasoning + context
- **Auto-stop on error** — halts on unhandled exceptions
- **Max API failures** — stops after N consecutive failures

## Backtesting

```bash
python -m trade_agent.backtest --config config.yaml
```

Runs any strategy plugin on historical data. Outputs: total return, win rate, Sharpe ratio, max drawdown.

## Deploy

### systemd
```bash
sudo cp trade-agent.service /etc/systemd/system/
sudo systemctl enable trade-agent
sudo systemctl start trade-agent
```

### Docker
```bash
docker-compose up -d  # Multi-instance with dashboard
```

## Project Structure

```
trade_agent/
├── agent.py              # Main loop
├── interfaces.py         # 6 abstract interfaces
├── plugin_loader.py      # Plugin discovery + loading
├── config.py             # YAML config + env var resolution
├── models.py             # Data models
├── storage.py            # SQLite persistence
├── risk.py               # Built-in risk profiles
├── backtest.py           # Historical replay engine
├── dashboard/            # Web dashboard (Phase 4)
│   ├── server.py
│   └── templates/
└── plugins/              # Built-in plugins
    ├── data_source/      # ccxt, csv
    ├── strategy/         # llm, rule, partial_exit, rule_builder
    ├── exchange/         # ccxt, paper, bybit_futures
    ├── notifier/         # telegram, discord, webhook, console
    ├── sentiment/        # rss_llm, none
    ├── risk_profile/     # conservative, moderate, aggressive, trailing_stop, kelly_sizing
    └── indicators/       # ta (RSI, MACD, EMA, BB, ATR)
```

## License

MIT

---

<div align="center">
<sub>v1.0.0 · 2026</sub>
</div>