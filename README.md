![version](https://img.shields.io/badge/version-0.1.0-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.11+-3776AB)

# Trade Agent

Modular AI trading agent with plugin system. LLM analyzes market data, news sentiment, and technical indicators — then makes informed trading decisions across multiple exchanges.

Every component (data source, strategy, exchange, notifier, sentiment, risk) is swappable via plugins implementing abstract interfaces. No framework. No lock-in.

---

<details>
<summary>🇮🇩 Bahasa Indonesia</summary>

## Apa ini?

Bot trading AI modular dengan sistem plugin. LLM analisa data market + news + indikator teknikal → decision → eksekusi trade.

Setiap komponen (data, strategi, exchange, notifikasi, sentiment, risk) bisa diganti via plugin. Nggak ada framework, nggak ada lock-in.

## Quick Start

```bash
git clone https://github.com/mocasus/trade-agent.git
cd trade-agent
pip install -e ".[all]"

# Copy + edit config
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
- **strategy**: llm (AI decision) | rule (config-based)
- **exchange**: ccxt (real) | paper (simulasi)
- **notifier**: telegram | discord | webhook | console
- **sentiment**: rss_llm | none
- **risk_profile**: conservative | moderate | aggressive

Bikin plugin custom: implement interface → taruh di `~/.trade-agent/plugins/`

## Safety

- Paper mode ON default — nggak bakal trade real money
- Paper mode forced 24h pertama
- Kill switch: Telegram `/stop`
- Daily loss limit hard stop
- Audit trail: semua decision + reasoning di-log

</details>

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
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│DataSource│ │ Strategy │ │ Exchange │ │ Notifier │
│ Plugins  │ │ Plugins  │ │ Plugins  │ │ Plugins  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
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

6 swappable slots, each behind an abstract interface:

| Slot | Interface | Built-in Plugins |
|------|-----------|-----------------|
| data_source | `DataSourceInterface` | ccxt, csv |
| strategy | `StrategyInterface` | llm, rule |
| exchange | `ExchangeInterface` | ccxt, paper |
| notifier | `NotifierInterface` | telegram, discord, webhook, console |
| sentiment | `SentimentInterface` | rss_llm, none |
| risk_profile | `RiskProfileInterface` | conservative, moderate, aggressive |
| indicators | `IndicatorPluginInterface` | ta (RSI, MACD, EMA, BB, ATR) |

**Custom plugin**: implement the interface → place in `~/.trade-agent/plugins/<slot>/`

```python
# ~/.trade-agent/plugins/strategy/my_quant.py
from trade_agent.interfaces import StrategyInterface
from trade_agent.models import Decision, MarketContext, Action

class MyQuantStrategy(StrategyInterface):
    def analyze(self, context: MarketContext) -> Decision:
        # Your logic here
        return Decision(action=Action.BUY, symbol=context.symbol, confidence=80, reasoning="...")

def register():
    return {"name": "my_quant", "class": MyQuantStrategy, "description": "Custom quant strategy"}
```

Then in config: `plugins.strategy: "my_quant"`

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

Three built-in profiles + custom via plugin:

| | Conservative | Moderate | Aggressive |
|---|---|---|---|
| Max position | 2% | 8% | 15% |
| Confidence floor | 70 | 65 | 55 |
| Stop-loss | ATR×1.0 | ATR×1.5 | ATR×2.0 |
| R:R ratio | 1.5 | 2.0 | 1.5 |
| Daily loss limit | 2% | 5% | 10% |
| Reserve | 20% | 10% | 5% |

All profiles respect config overrides. Position sizing: fixed %, Kelly criterion, or volatility-adjusted (configurable).

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

## Deploy as Service

```bash
sudo cp trade-agent.service /etc/systemd/system/
sudo systemctl enable trade-agent
sudo systemctl start trade-agent
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
└── plugins/              # Built-in plugins
    ├── data_source/      # ccxt, csv
    ├── strategy/         # llm, rule
    ├── exchange/         # ccxt, paper
    ├── notifier/         # telegram, discord, webhook, console
    ├── sentiment/        # rss_llm, none
    ├── risk_profile/     # conservative, moderate, aggressive
    └── indicators/       # ta (RSI, MACD, EMA, BB, ATR)
```

## License

MIT

---

![version](https://img.shields.io/badge/version-0.1.0-blue) ![license](https://img.shields.io/badge/license-MIT-green)
