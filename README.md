<p align="center">
  <img src="assets/logo.png" width="128" height="128" alt="Trade Agent Logo">
</p>

<h1 align="center">Trade Agent</h1>

<p align="center">
  Modular AI trading agent with plugin system.<br>
  LLM analyzes market + news + indicators → decision → execution.<br>
  Every component swappable. No framework. No lock-in.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="license">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="python">
  <a href="TESTS.md"><img src="https://img.shields.io/badge/tests-39%20✅-brightgreen?style=flat-square&logo=pytest&logoColor=white" alt="tests"></a>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square&logo=codecov&logoColor=white" alt="coverage">
  <img src="https://img.shields.io/badge/code%20style-ruff-261230?style=flat-square&logo=ruff&logoColor=white" alt="code style">
  <img src="https://img.shields.io/badge/LOC-3,722-orange?style=flat-square" alt="LOC">
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/mocasus/trade-agent?style=flat-square&logo=github&label=stars&cacheSeconds=86400" alt="stars">
  <img src="https://img.shields.io/github/forks/mocasus/trade-agent?style=flat-square&logo=github&label=forks&cacheSeconds=86400" alt="forks">
  <img src="https://img.shields.io/github/issues/mocasus/trade-agent?style=flat-square&logo=github&label=issues" alt="issues">
  <img src="https://img.shields.io/github/last-commit/mocasus/trade-agent?style=flat-square&logo=git&label=last%20commit" alt="last commit">
  <img src="https://img.shields.io/github/repo-size/mocasus/trade-agent?style=flat-square&logo=github&label=size" alt="repo size">
  <img src="https://img.shields.io/github/languages/count/mocasus/trade-agent?style=flat-square&logo=github&label=languages" alt="languages">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20WSL-5996B8?style=flat-square&logo=linux&logoColor=white" alt="platform">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="docker">
  <img src="https://img.shields.io/badge/systemd-service-3DA6E8?style=flat-square&logo=systemd&logoColor=white" alt="systemd">
  <img src="https://img.shields.io/badge/SQLite-storage-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="sqlite">
  <img src="https://img.shields.io/badge/ccxt-100%2B%20exchanges-42C8D0?style=flat-square&logo=binance&logoColor=white" alt="ccxt">
  <img src="https://img.shields.io/badge/PRs-welcome-2ea44f?style=flat-square&logo=github&logoColor=white" alt="PRs welcome">
</p>

---

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/🚀_Quick_Start-2ea44f?style=flat-square" alt="Quick Start"></a>
  <a href="#features"><img src="https://img.shields.io/badge/✨_Features-58a6ff?style=flat-square" alt="Features"></a>
  <a href="#plugin-system"><img src="https://img.shields.io/badge/🧩_Plugins-F78C40?style=flat-square" alt="Plugins"></a>
  <a href="#advanced-features"><img src="https://img.shields.io/badge/🔬_Advanced-d73a4a?style=flat-square" alt="Advanced"></a>
  <a href="#risk-profiles"><img src="https://img.shields.io/badge/🛡️_Risk-ffd33d?style=flat-square" alt="Risk"></a>
  <a href="TESTS.md"><img src="https://img.shields.io/badge/🧪_Tests-8b949e?style=flat-square" alt="Tests"></a>
  <a href="#deploy"><img src="https://img.shields.io/badge/🐳_Deploy-2496ED?style=flat-square" alt="Deploy"></a>
</p>

<details>
<summary>🇮🇩 Bahasa Indonesia</summary>

## Apa ini?

Bot trading AI modular dengan sistem plugin. LLM analisa data market + news + indikator teknikal → decision → eksekusi trade.

Setiap komponen bisa diganti via plugin. Nggak ada framework, nggak ada lock-in.

## Quick Start

```bash
git clone https://github.com/mocasus/trade-agent.git
cd trade-agent
pip install -e ".[all]"
cp config.example.yaml config.yaml

echo "AI_API_KEY=sk-xxx" >> .env
echo "BINANCE_API_KEY=xxx" >> .env
echo "BINANCE_API_SECRET=xxx" >> .env

python -m trade_agent --config config.yaml  # Paper mode default
```

## Plugin System

6 slot yang bisa diganti:
- **data_source**: ccxt | csv
- **strategy**: llm | rule | partial_exit | rule_builder
- **exchange**: ccxt | paper | bybit_futures
- **notifier**: telegram | discord | webhook | console
- **sentiment**: rss_llm | none
- **risk_profile**: conservative | moderate | aggressive | trailing_stop | kelly_sizing

## Safety

- Paper mode ON default
- Paper mode forced 24h pertama
- Kill switch: Telegram `/stop`
- Daily loss limit hard stop
- Audit trail: semua decision di-log

</details>

---

## ✨ Features

- 🧩 **Plugin system** — 7 swappable slots, 21 built-in plugins
- 🤖 **LLM strategy** — OpenAI-compatible API analyzes market context → structured decision
- 📊 **Technical indicators** — RSI, MACD, EMA, Bollinger Bands, ATR
- 🔄 **Trailing stop-loss** — follows price up, never goes down
- 📐 **Kelly criterion** — optimal fractional position sizing
- 🎯 **Partial exits** — scaled exits at profit levels (25%/25%/50%)
- 📋 **Rule builder** — config-only strategy, no code needed
- 📰 **News sentiment** — RSS + LLM sentiment analysis
- 🔔 **Multi-notifier** — Telegram, Discord, webhook, console
- 📈 **Backtest engine** — historical replay + Sharpe/drawdown/win rate
- 🖥️ **Web dashboard** — dark theme, real-time portfolio monitoring
- 🐳 **Docker compose** — multi-instance deployment
- 🛡️ **Safety-first** — paper mode default, kill switch, daily loss limit, audit trail

## Quick Start

```bash
git clone https://github.com/mocasus/trade-agent.git
cd trade-agent
pip install -e ".[all]"
cp config.example.yaml config.yaml  # Edit before running

echo "AI_API_KEY=sk-xxx" >> .env
echo "BINANCE_API_KEY=xxx" >> .env

python -m trade_agent --config config.yaml  # Paper mode by default
```

## Architecture

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│DataSource│ │ Strategy │ │ Exchange │ │ Notifier │ │Sentiment │
│ ccxt/csv │ │llm/rule  │ │paper/real│ │ TG/Disc  │ │ rss_llm  │
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

Core loop only knows interfaces. Swap any plugin without touching core.

## Plugin System

| Slot | Interface | Built-in Plugins |
|------|-----------|-----------------|
| data_source | `DataSourceInterface` | ccxt, csv |
| strategy | `StrategyInterface` | llm, rule, partial_exit, rule_builder |
| exchange | `ExchangeInterface` | ccxt, paper, bybit_futures |
| notifier | `NotifierInterface` | telegram, discord, webhook, console |
| sentiment | `SentimentInterface` | rss_llm, none |
| risk_profile | `RiskProfileInterface` | conservative, moderate, aggressive, trailing_stop, kelly_sizing |
| indicators | `IndicatorPluginInterface` | ta (RSI, MACD, EMA, BB, ATR) |

**Custom plugin** — implement interface → place in `~/.trade-agent/plugins/<slot>/`

```python
# ~/.trade-agent/plugins/strategy/my_quant.py
from trade_agent.interfaces import StrategyInterface
from trade_agent.models import Decision, MarketContext, Action

class MyQuantStrategy(StrategyInterface):
    def analyze(self, context: MarketContext) -> Decision:
        return Decision(action=Action.BUY, symbol=context.symbol,
                        confidence=80, reasoning="...")

def register():
    return {"name": "my_quant", "class": MyQuantStrategy}
```

Config: `plugins.strategy: "my_quant"`

## Advanced Features

### Trailing Stop-Loss

```yaml
risk:
  method: trailing_stop
  trailing_stop:
    activation_threshold: 0.03  # Activate after 3% profit
    trail_percent: 0.015        # Trail 1.5% below peak
```

### Kelly Criterion Sizing

```yaml
risk:
  position_sizing:
    method: kelly
    kelly_fraction: 0.5  # Half-Kelly (recommended)
```

### Bybit Futures

```yaml
plugins:
  exchange: bybit_futures
exchange:
  bybit_futures:
    leverage: 3
    margin_mode: cross
```

### Partial Exit

```yaml
strategy:
  partial_exit:
    levels:
      - profit_pct: 5,  exit_pct: 25
      - profit_pct: 10, exit_pct: 25
      - profit_pct: 15, exit_pct: 50
```

### Rule Builder

```yaml
strategy:
  rule_builder:
    rules:
      - name: "RSI oversold buy"
        conditions: [{indicator: rsi, operator: "<", value: 30}]
        action: buy, confidence: 75
      - name: "MACD sell"
        conditions: [{indicator: macd_histogram, operator: "<", value: 0}]
        action: sell, confidence: 70
```

### Web Dashboard

```bash
python -m trade_agent.dashboard --config config.yaml  # :8080
```

## Risk Profiles

| | Conservative | Moderate | Aggressive | Trailing Stop | Kelly |
|---|---|---|---|---|---|
| Max position | 2% | 8% | 15% | 10% | Dynamic |
| Confidence floor | 70 | 65 | 55 | 60 | 60 |
| Stop-loss | ATR×1.0 | ATR×1.5 | ATR×2.0 | Trail 1.5% | ATR×1.5 |
| R:R ratio | 1.5 | 2.0 | 1.5 | Variable | 2.0 |
| Daily loss limit | 2% | 5% | 10% | 5% | 5% |

## 🛡️ Safety

- **Paper mode ON by default** — won't trade real money
- **Paper mode forced 24h** — can't accidentally go live
- **Kill switch** — Telegram `/stop` halts immediately
- **Daily loss limit** — hard stop, AI can't override
- **Max position size** — AI can't exceed configured %
- **Audit trail** — every decision logged with reasoning
- **Auto-stop on error** — halts on unhandled exceptions
- **Max API failures** — stops after N consecutive failures

## Backtesting

```bash
python -m trade_agent.backtest --config config.yaml
```

Outputs: total return, win rate, Sharpe ratio, max drawdown.

📋 **[Full test results →](TESTS.md)** — 39 tests, 7 suites, all passing.

## Deploy

### systemd

```bash
sudo cp trade-agent.service /etc/systemd/system/
sudo systemctl enable --now trade-agent
```

### Docker

```bash
docker-compose up -d
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
├── dashboard/            # Web dashboard
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

<p align="center">
  <strong>Made with</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/YAML-CB171E?style=for-the-badge&logo=yaml&logoColor=white" alt="YAML">
  <img src="https://img.shields.io/badge/pytest-0A9ED4?style=for-the-badge&logo=pytest&logoColor=white" alt="pytest">
</p>

<p align="center">
  <strong>Supported Exchanges</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Binance-F3BA2F?style=for-the-badge&logo=binance&logoColor=black" alt="Binance">
  <img src="https://img.shields.io/badge/Bybit-F7A600?style=for-the-badge&logo=bybit&logoColor=white" alt="Bybit">
  <img src="https://img.shields.io/badge/OKX-FFFFFF?style=for-the-badge&logo=okx&logoColor=black" alt="OKX">
  <img src="https://img.shields.io/badge/Coinbase-0052FF?style=for-the-badge&logo=coinbase&logoColor=white" alt="Coinbase">
  <img src="https://img.shields.io/badge/100%2B_More-FF6B6B?style=for-the-badge&logo=ccxt&logoColor=white" alt="100+ More">
</p>

<p align="center">
  <strong>Integrations</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram">
  <img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord">
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/Webhooks-FF6B6B?style=for-the-badge&logo=webhooks&logoColor=white" alt="Webhooks">
</p>

<p align="center">
  <strong>Status</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Phase_1-✅_Complete-2ea44f?style=flat-square" alt="Phase 1">
  <img src="https://img.shields.io/badge/Phase_2-✅_Complete-2ea44f?style=flat-square" alt="Phase 2">
  <img src="https://img.shields.io/badge/Phase_3-✅_Complete-2ea44f?style=flat-square" alt="Phase 3">
  <img src="https://img.shields.io/badge/Phase_4-✅_Complete-2ea44f?style=flat-square" alt="Phase 4">
  <img src="https://img.shields.io/badge/Paper_Mode-🟢_Active-2ea44f?style=flat-square" alt="Paper Mode">
</p>

---

<p align="center">
  <sub>v1.0.0 · 2026 · Built by <a href="https://github.com/mocasus">@mocasus</a></sub>
</p>