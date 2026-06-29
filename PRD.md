# PRD — Trade Agent

> AI-powered automated trading agent. Modular architecture with plugin system and abstraction layers — LLM analyzes market data, news sentiment, and technical indicators to make informed trading decisions across multiple exchanges.

**Status:** Draft — pending approval
**Author:** mocasus
**License:** MIT

---

## 1. Problem

Existing trading bots are either:
- **Rule-based** (fixed strategies, can't adapt to changing market conditions)
- **SaaS lock-in** (no code visibility, monthly fees, your money on their keys)
- **Monolithic** (hard to extend, swap components, or add custom strategies)
- **Over-engineered** (thousands of lines, 20+ dependencies, impossible to audit)

There's no modular, plugin-driven trading agent where an LLM actually **reasons** about market state and makes execution decisions — with the extensibility to swap exchanges, strategies, data sources, and notification channels without touching core code.

## 2. What This Is

A Python trading agent with **abstraction layers + plugin system** that uses LLMs to:
1. Pull market data via pluggable data sources
2. Ingest news/sentiment via pluggable sentiment providers
3. Feed everything to a pluggable strategy engine (LLM-based by default)
4. Parse the strategy's decision (BUY / SELL / HOLD) with reasoning
5. Execute via pluggable exchange adapters
6. Report via pluggable notifiers (Telegram, Discord, webhook, etc.)

**What it's NOT:**
- Not a HFT / arbitrage bot (latency in seconds, not microseconds)
- Not a "guaranteed profit" system (trading is risky, this is a tool)
- Not a SaaS (self-hosted, your keys, your money)

## 3. Target Users

- Developers who want AI-assisted trading without SaaS lock-in
- Traders who want to customize strategies via plugins, not config hacks
- Tinkerers who want to swap exchanges, indicators, or AI models easily
- Quant devs who want to backtest custom strategies on historical data
- People who run a VPS and want a trading bot as a systemd service

## 4. Core Features

### 4.1 Market Data (Pluggable)
- Exchange REST API via adapters (Binance, Bybit, OKX, custom)
- Real-time price, order book depth, 24h volume
- Technical indicators via plugin: RSI, MACD, EMA, BB, custom combos
- Candle data: configurable timeframes
- **Plugin hook**: `data_source` — any class implementing `DataSourceInterface` can inject market data (e.g., WebSocket feeds, custom APIs, CSV imports)

### 4.2 AI Decision Engine (Pluggable Strategy)
- **Default strategy**: LLM prompt with market context + indicators + news → decision
- **Custom strategies**: any class implementing `StrategyInterface` (rule-based, hybrid LLM+rules, pure quant)
- LLM output: JSON `{action, symbol, amount_pct, reasoning, confidence, metadata}`
- Action types: `BUY`, `SELL`, `HOLD`, `CLOSE_ALL`, `SET_STOP_LOSS`, `SET_TRAILING_STOP`
- Confidence score (0-100): below threshold → skip execution
- Multi-model support: any OpenAI-compatible endpoint
- **Plugin hook**: `strategy` — swap the entire decision engine without touching core

### 4.3 News & Sentiment (Pluggable)
- RSS feed aggregation (CryptoSlate, CoinDesk, custom feeds)
- X/Twitter sentiment via API (optional plugin)
- LLM summarizes + sentiment score (optional, disable per config)
- **Plugin hook**: `sentiment` — custom sentiment providers (on-chain analytics, fear-greed index, social volume, etc.)

### 4.4 Risk Management (Pluggable Profile)
- **Risk profiles**: predefined profiles (conservative, moderate, aggressive) + custom
- **Position sizing**: fixed %, Kelly criterion, volatility-adjusted — selectable per profile
- **Stop-loss**: ATR-based, fixed %, trailing — configurable per profile
- **Take-profit**: risk-reward ratio, fixed %, partial exit — configurable
- **Max open positions**, **Daily loss limit**, **Cooldown** — all per-profile
- **Plugin hook**: `risk_profile` — custom risk calculation logic

### 4.5 Execution (Pluggable Exchange)
- Exchange adapters: Binance (spot), Bybit (spot/futures), OKX, custom
- Order types: market, limit, OCO — adapter-dependent
- Slippage protection: configurable max deviation
- Paper trading mode: simulate without real funds (default ON)
- **Plugin hook**: `exchange` — any class implementing `ExchangeInterface`

### 4.6 Portfolio & Reporting (Pluggable Notifier)
- Real-time portfolio value
- Trade history with P&L per trade
- Daily/weekly/monthly summary reports
- **Plugin hook**: `notifier` — Telegram, Discord, webhook, email, Slack, Matrix, or custom
- Alert categories configurable per notifier: trade, stop_loss, daily_report, error, kill_switch

### 4.7 Backtesting
- Historical data replay (exchange kline API or CSV import)
- Run any strategy plugin on historical candles
- Simulate execution with realistic slippage + fees
- Performance report: total return, win rate, Sharpe ratio, max drawdown
- Export results as JSON/CSV

## 5. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Plugin Registry                          │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │DataSource│ │ Strategy │ │ Exchange │ │ Notifier │       │
│  │ Plugins  │ │ Plugins  │ │ Plugins  │ │ Plugins  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐                                  │
│  │Sentiment │ │  Risk    │                                  │
│  │ Plugins  │ │ Profiles │                                  │
│  └──────────┘ └──────────┘                                  │
└─────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Data Layer  │────▶│  Strategy    │────▶│  Execution  │
│  (Interface) │     │  (Interface) │     │  (Interface)│
└─────────────┘     └──────────────┘     └─────────────┘
                                               │
                    ┌──────────────┐           ▼
                    │   Storage    │     ┌─────────────┐
                    │              │     │  Notifier   │
                    │ • SQLite DB  │     │  (Interface)│
                    │ • Trade log  │     └─────────────┘
                    │ • Decisions  │
                    └──────────────┘
```

### Abstraction Layers (Interfaces)

Every major component is behind an interface. Core loop only knows interfaces — never concrete implementations.

```python
class DataSourceInterface:
    """Fetch market data (candles, orderbook, ticker)."""
    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]
    def get_ticker(self, symbol: str) -> Ticker
    def get_orderbook(self, symbol: str, depth: int) -> OrderBook

class StrategyInterface:
    """Decide what to do based on market context."""
    def analyze(self, context: MarketContext) -> Decision

class ExchangeInterface:
    """Execute trades on an exchange."""
    def place_order(self, order: Order) -> OrderResult
    def cancel_order(self, order_id: str) -> bool
    def get_balance(self) -> Balance
    def get_positions(self) -> list[Position]

class NotifierInterface:
    """Send alerts to users."""
    def send(self, event: Event) -> bool
    def send_report(self, report: Report) -> bool

class SentimentInterface:
    """Fetch + score news sentiment."""
    def get_sentiment(self, symbol: str) -> SentimentScore

class RiskProfileInterface:
    """Calculate position size, stop-loss, take-profit."""
    def calculate_position_size(self, capital: float, confidence: int) -> float
    def calculate_stop_loss(self, entry_price: float, context: MarketContext) -> float
    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float
    def check_risk_rules(self, portfolio: Portfolio, decision: Decision) -> bool
```

### Plugin System

Plugins are Python modules discovered at runtime from `plugins/` directory or registered in `config.yaml`. Each plugin implements one of the interfaces above.

**Discovery & Loading:**
```python
# Built-in plugins live in trade_agent/plugins/<type>/
# User plugins live in ~/.trade-agent/plugins/<type>/
# Config overrides specify which plugin to use per slot

plugin_registry = {
    "data_source": "ccxt",           # built-in
    "strategy": "llm",               # built-in
    "exchange": "binance",           # built-in
    "notifier": ["telegram"],        # multiple notifiers allowed
    "sentiment": "rss_llm",          # built-in
    "risk_profile": "conservative",  # built-in profile name
}

# Custom plugin:
plugin_registry = {
    "strategy": "my_quant_strategy",  # ~/.trade-agent/plugins/strategy/my_quant_strategy.py
}
```

**Plugin file structure:**
```
~/.trade-agent/plugins/
├── strategy/
│   ├── my_quant_strategy.py    # implements StrategyInterface
│   └── grid_trader.py          # implements StrategyInterface
├── sentiment/
│   ├── fear_greed_index.py     # implements SentimentInterface
│   └── on_chain.py             # implements SentimentInterface
├── notifier/
│   └── discord_notifier.py     # implements NotifierInterface
└── exchange/
    └── okx_adapter.py          # implements ExchangeInterface
```

Each plugin file must:
1. Implement the corresponding interface
2. Have a `register()` function returning `{name, class, description}`
3. Be importable without extra dependencies beyond core deps

### Design Principles
- **Interface-first** — core loop never imports concrete plugins directly
- **Plugin-driven** — every slot (data, strategy, exchange, notifier, sentiment, risk) is swappable
- **No web framework** — Telegram/Discord/webhook for interaction, no Flask/Django
- **SQLite** for persistence (no Postgres, no Redis)
- **systemd service** for deployment
- **Config in YAML** — deep customization without code changes
- **Minimal core deps**: `ccxt`, `pyyaml`, `openai`, `httpx`, `apscheduler`
- **Plugin deps** are optional — only installed if that plugin is used

## 6. Project Structure

```
trade-agent/
├── trade_agent/                  # Core package
│   ├── __init__.py
│   ├── agent.py                  # Main loop: data → strategy → risk → execute → notify
│   ├── interfaces.py             # All abstract interfaces (DataSource, Strategy, Exchange, etc.)
│   ├── plugin_loader.py          # Plugin discovery, registration, validation
│   ├── config.py                 # YAML config loader + validation + defaults
│   ├── risk.py                   # Built-in risk profiles (conservative, moderate, aggressive)
│   ├── storage.py                # SQLite trade log, decisions, portfolio state
│   ├── models.py                 # Data models: Candle, Ticker, Decision, Order, Position, etc.
│   ├── backtest.py               # Historical replay engine (works with any strategy plugin)
│   └── plugins/                  # Built-in plugins
│       ├── __init__.py
│       ├── data_source/
│       │   ├── ccxt_source.py    # ccxt-based data (Binance, Bybit, 100+ exchanges)
│       │   └── csv_source.py     # CSV import for backtesting
│       ├── strategy/
│       │   ├── llm_strategy.py   # Default: LLM prompt → JSON decision
│       │   └── rule_strategy.py  # Simple rule-based (RSI < 30 → BUY, etc.)
│       ├── exchange/
│       │   ├── ccxt_exchange.py  # ccxt-based execution (same adapter as data_source)
│       │   └── paper_exchange.py # Paper trading simulator
│       ├── sentiment/
│       │   ├── rss_llm.py        # RSS feeds + LLM sentiment scoring
│       │   └── none.py           # Disable sentiment entirely
│       ├── notifier/
│       │   ├── telegram.py       # Telegram bot alerts + commands
│       │   ├── discord.py        # Discord webhook alerts
│       │   ├── console.py        # stdout (for debugging)
│       │   └── webhook.py        # Generic HTTP webhook
│       └── risk_profile/
│           ├── conservative.py   # 2% position, tight stops
│           ├── moderate.py       # 5% position, moderate stops
│           ├── aggressive.py     # 10% position, loose stops
│       └── indicators/
│           ├── ta_indicators.py  # pandas-ta based (RSI, MACD, EMA, BB)
│           └── custom.py         # User-defined indicator combos
├── plugins/                      # User plugins directory (gitignored)
│   └── ...
├── config.example.yaml           # Full config with all options documented
├── requirements.txt              # Core deps only
├── pyproject.toml                # Package metadata
├── PRD.md                        # This document
├── README.md                     # Setup guide (ID/EN toggle)
├── LICENSE                       # MIT
└── .gitignore
```

**~15 core files + built-in plugins. No web framework. Full extensibility via plugin interfaces.**

## 7. Configuration

Config supports deep customization per plugin slot, risk profile, strategy parameters, and notification routing.

```yaml
# config.yaml — Full Customizable Configuration

# ── General ──
agent:
  name: "trade-agent-v1"          # Instance name (for multi-instance setups)
  log_level: "INFO"               # DEBUG, INFO, WARNING, ERROR
  log_file: "~/.trade-agent/logs/agent.log"
  data_dir: "~/.trade-agent"      # Base directory for DB, plugins, logs
  timezone: "Asia/Jakarta"        # For scheduling and reporting

# ── Plugin Registry ──
# Each slot selects which plugin to load. Built-in plugins are referenced
# by name; custom plugins by module path or file name in plugins/ dir.
plugins:
  data_source: "ccxt"             # built-in: ccxt, csv
  strategy: "llm"                 # built-in: llm, rule | custom: any StrategyInterface
  exchange: "ccxt"                # built-in: ccxt, paper
  notifier: ["telegram"]          # built-in: telegram, discord, console, webhook (list = multiple)
  sentiment: "rss_llm"            # built-in: rss_llm, none | custom: any SentimentInterface
  risk_profile: "moderate"        # built-in: conservative, moderate, aggressive | custom
  indicators: "ta"                # built-in: ta, custom

# ── Data Source ──
data_source:
  # ccxt-specific config (only used when plugins.data_source = "ccxt")
  exchange: "binance"             # Exchange name for ccxt (binance, bybit, okx, kraken, ...)
  api_key: "${BINANCE_API_KEY}"   # Env var reference (resolved at runtime)
  api_secret: "${BINANCE_API_SECRET}"
  testnet: true                   # Use exchange testnet (default ON for safety)
  rate_limit: true                # Respect ccxt rate limits
  # csv-specific config (only used when plugins.data_source = "csv")
  csv_path: "~/.trade-agent/data/history.csv"
  csv_format: "binance_klines"   # binance_klines, generic_ohlcv

# ── Strategy ──
strategy:
  # LLM strategy config (only used when plugins.strategy = "llm")
  ai:
    base_url: "${AI_BASE_URL}"    # Any OpenAI-compatible endpoint
    api_key: "${AI_API_KEY}"
    model: "gpt-4o-mini"          # Or local: llama, qwen, glm, etc.
    temperature: 0.3              # Low temp for consistent decisions
    max_tokens: 500               # Keep responses concise
    timeout_seconds: 30
    retry_on_failure: 2           # Retry count on API errors
    fallback_model: "gpt-4o-mini" # Backup model if primary fails
  # Prompt customization
  prompt:
    template: "default"           # built-in: default, conservative, aggressive
    custom_template: ""           # Path to custom prompt template file
    system_prompt: "You are a disciplined trading analyst..."
    include_indicators: true       # Inject indicator data into prompt
    include_news: true            # Inject news sentiment into prompt
    include_portfolio: true       # Inject current portfolio state
    include_reasoning_chain: false # Ask LLM to show step-by-step reasoning
    max_news_items: 5             # How many news items to include
    indicator_set: ["rsi", "macd", "ema_20", "ema_50", "bb"]  # Select which indicators
    timeframe_context: ["15m", "1h", "4h"]  # Multi-timeframe analysis
  # Decision parsing
  decision:
    action_types: ["BUY", "SELL", "HOLD", "CLOSE_ALL"]  # Allowed actions
    confidence_threshold: 65       # Min confidence to execute (0-100)
    require_reasoning: true        # Reject decisions without reasoning
    max_amount_pct: 15            # Cap: LLM can't request more than this %

  # Rule strategy config (only used when plugins.strategy = "rule")
  rules:
    - name: "rsi_oversold"
      condition: "rsi < 30"
      action: "BUY"
      amount_pct: 5
    - name: "rsi_overbought"
      condition: "rsi > 70"
      action: "SELL"
      amount_pct: 5

# ── Risk Profile ──
risk:
  profile: "moderate"             # Selects built-in risk profile
  # Override any profile setting with explicit values:
  position_sizing:
    method: "fixed_pct"           # fixed_pct, kelly, volatility_adjusted
    max_pct: 8                    # Max % of available capital per trade
    min_pct: 1                    # Min % (floor for small-confidence trades)
  stop_loss:
    method: "atr"                 # fixed_pct, atr, trailing
    atr_multiplier: 1.5           # ATR-based: stop = entry - ATR*1.5
    fixed_pct: 2                  # Fixed: stop = entry * (1 - 0.02)
    trailing_pct: 1.5             # Trailing: follows price up by 1.5%
    trailing_activation_pct: 1    # Activate trailing after 1% profit
  take_profit:
    method: "rr_ratio"            # fixed_pct, rr_ratio, partial
    rr_ratio: 2                   # TP = entry + (entry - stop) * 2
    fixed_pct: 4
    partial_exit_steps: []        # [{pct: 50, at_profit: 2}, {pct: 50, at_profit: 5}]
  daily_limits:
    max_loss_pct: 5               # Stop trading if daily loss > 5%
    max_trades: 20                # Max trades per day
    max_open_positions: 5         # Max concurrent open positions
    cooldown_minutes: 30          # Min time between trades per symbol
    max_consecutive_losses: 3     # Pause after N consecutive losses
  portfolio:
    reserve_pct: 10               # Keep 10% of capital as reserve (never trade)

# ── Trading ──
trading:
  symbols:
    - symbol: "BTCUSDT"
      enabled: true
      timeframe: "15m"
      strategy_override: ""       # Use different strategy for specific symbol
      risk_override: ""           # Use different risk profile for specific symbol
    - symbol: "ETHUSDT"
      enabled: true
      timeframe: "15m"
    - symbol: "SOLUSDT"
      enabled: false              # Disabled but configured
      timeframe: "5m"
  paper_mode: true                # Simulate trades (default ON, MUST be ON for first run)
  fee_pct: 0.1                   # Trading fee assumption (for P&L calc + backtest)
  slippage_pct: 0.05             # Expected slippage (for paper mode + backtest)

# ── Sentiment ──
sentiment:
  enabled: true                   # Global toggle
  # rss_llm config (when plugins.sentiment = "rss_llm")
  feeds:
    - url: "https://cryptoslate.com/feed/"
      weight: 1.0                 # Feed importance multiplier
    - url: "https://www.coindesk.com/arc/outboundfeeds/rss/"
      weight: 1.0
    - url: "https://cointelegraph.com/rss"
      weight: 0.8
  max_items: 10                   # Max news items to process per cycle
  cache_hours: 2                  # Don't re-fetch news within this window
  symbol_filter: true             # Only include news mentioning traded symbols
  # LLM sentiment scoring
  sentiment_prompt: "brief"       # built-in: brief, detailed
  sentiment_model_override: ""    # Use cheaper model for sentiment (e.g., gpt-4o-mini)

# ── Notifiers ──
notifiers:
  telegram:
    bot_token: "${TG_BOT_TOKEN}"
    chat_id: "${TG_CHAT_ID}"
    alerts: [trade, stop_loss, daily_report, error, kill_switch]
    commands: true                # Enable /start, /stop, /status, /portfolio, /force_buy, /force_sell
    daily_report_time: "21:00"    # When to send daily summary
    daily_report_timezone: "Asia/Jakarta"
  discord:
    webhook_url: "${DISCORD_WEBHOOK}"
    alerts: [trade, stop_loss, error]
  webhook:
    url: "https://your-server.com/api/trade-alert"
    method: "POST"
    headers: {"Authorization": "Bearer ${WEBHOOK_TOKEN}"}
    alerts: [trade, stop_loss]
  console:
    alerts: [all]                 # Print everything to stdout (debugging)

# ── Scheduling ──
schedule:
  interval_minutes: 15            # Run main loop every N minutes
  backfill_on_start: true         # Fetch recent candles on startup
  missed_ticks_grace: 5           # If agent was down, process up to N missed ticks

# ── Backtesting ──
backtest:
  start_date: "2025-01-01"
  end_date: "2025-06-01"
  initial_capital: 10000
  symbols: ["BTCUSDT"]
  timeframe: "15m"
  strategy: "llm"                 # Use any strategy plugin
  paper_mode: true                # Always true for backtest
  output_format: "json"           # json, csv, markdown
  output_path: "~/.trade-agent/backtest-results/"

# ── Storage ──
storage:
  db_path: "~/.trade-agent/trade-agent.db"
  backup_on_start: true           # Auto-backup DB on agent start
  backup_dir: "~/.trade-agent/backups/"
  retention_days: 90              # Auto-purge decisions older than N days

# ── Safety ──
safety:
  paper_mode_required_first_run: true  # Force paper mode for first 24h
  kill_switch_enabled: true            # Telegram /stop command
  auto_stop_on_error: true             # Halt on unhandled exception
  max_api_failures: 5                  # Stop after N consecutive API failures
  notify_on_kill: true                 # Send alert when agent is killed
```

## 8. Decision Prompt (Core)

Prompt template is configurable. Default template:

```
You are a disciplined trading analyst. Analyze the following market data and make a decision.

## Market: {symbol} ({timeframes} timeframe)
Current price: {price}
24h change: {change_24h}%
Volume: {volume_24h}

## Indicators
{indicators_block}

## Recent News (last {news_window}h)
{news_block}

## Current Portfolio
Available capital: {available_capital}
Open positions: {positions}
Today's P&L: {daily_pnl}

## Risk Parameters
Max position: {max_position_pct}% of capital
Stop-loss method: {stop_loss_method}
Daily loss limit: {daily_loss_limit_pct}%

## Decision
Respond as JSON:
{
  "action": "BUY" | "SELL" | "HOLD" | "CLOSE_ALL",
  "symbol": "{symbol}",
  "amount_pct": 5,
  "confidence": 75,
  "reasoning": "Brief explanation",
  "indicators_used": ["rsi", "macd"],
  "news_factors": ["ETF approval", "regulatory delay"]
}
```

Custom templates: create a markdown file, reference it in `strategy.prompt.custom_template`.

## 9. Roadmap

### Phase 1 — Core + Plugin System (v0.1)
- [ ] Interface definitions (all 6 abstract classes)
- [ ] Plugin loader (discovery, registration, validation)
- [ ] Built-in plugins: ccxt_source, llm_strategy, ccxt_exchange, paper_exchange, telegram_notifier, console_notifier
- [ ] Built-in risk profiles (conservative, moderate, aggressive)
- [ ] Built-in indicators (RSI, MACD, EMA, BB)
- [ ] Main agent loop (data → strategy → risk check → execute → notify)
- [ ] SQLite storage (trades, decisions, portfolio)
- [ ] Deep config with env var resolution
- [ ] systemd service template

### Phase 2 — Sentiment + Backtest (v0.2)
- [ ] RSS + LLM sentiment plugin
- [ ] Backtesting engine (works with any strategy plugin)
- [ ] Performance metrics (Sharpe, drawdown, win rate)
- [ ] CSV data source plugin (for backtest imports)
- [ ] Discord + webhook notifier plugins

### Phase 3 — Multi-exchange + Advanced Risk (v0.3)
- [ ] Bybit futures adapter
- [ ] Trailing stop-loss risk profile
- [ ] Partial exit strategy
- [ ] Kelly criterion position sizing
- [ ] OCO order support

### Phase 4 — Community (v0.4+)
- [ ] Plugin marketplace / registry (git-based)
- [ ] Rule-based strategy builder (config-only, no code)
- [ ] Web dashboard (minimal, read-only, built with vanilla HTML + JS)
- [ ] Multi-language README (ID/EN)
- [ ] Docker image
- [ ] Multi-instance support (run multiple agents with different configs)

## 10. Non-Goals

- **Not a copy-trading platform** — this trades its own decisions, not mirroring others
- **Not an exchange** — no order matching, no custody
- **Not financial advice** — users responsible for their own money
- **Not HFT** — decisions take seconds, not microseconds
- **No web framework** — no Flask/Django/FastAPI for the agent core. Notifiers are the UI. Dashboard is optional Phase 4 vanilla HTML.

## 11. Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Standard for trading/AI, ccxt ecosystem |
| Exchange API | `ccxt` | Unified API for 100+ exchanges |
| LLM Client | `openai` SDK | Works with any OpenAI-compatible endpoint |
| Indicators | `pandas-ta` | Lightweight, comprehensive indicator library |
| Storage | SQLite (`sqlite3`) | Zero-config, single file |
| Config | YAML (`pyyaml`) | Human-readable, deep nesting |
| Plugin Loader | Custom (no dependency) | Dynamic import + interface validation |
| Scheduling | `apscheduler` | In-process, no cron/celery |
| Notifier - TG | `python-telegram-bot` | Full async, command handling |
| Notifier - Discord | `httpx` (raw webhook) | Minimal, no SDK needed |

**Core deps: ~8 packages. Plugin deps are optional — only installed if needed. No web framework, no ORM, no message queue.**

## 12. Safety

- **Paper mode ON by default** — new users start simulated
- **Paper mode forced for first 24h** — `safety.paper_mode_required_first_run`
- **Testnet first** — exchange testnet before mainnet
- **No leverage by default** — spot only in Phase 1
- **Daily loss limit** — hard stop, can't be overridden by AI or plugins
- **Max position size** — AI/plugins can't exceed configured %
- **Max API failures** — halt after N consecutive failures
- **Kill switch** — Telegram `/stop` halts agent immediately
- **Auto-stop on error** — halt on unhandled exception
- **Audit trail** — every decision logged with full context + reasoning
- **Notify on kill** — alert user when agent is halted

## 13. Open Source Considerations

- **License:** MIT (max permissive)
- **No API keys in repo** — `.env` + `.gitignore`
- **No AI/agent credits** — clean authorship (per user preference)
- **README:** 🇮🇩/🇬🇧 toggle with `<details>` tags
- **Logo:** 2-3 color geometric, no text (Stripe/Vercel style)
- **Version badge** in README header + footer
- **Plugin contributions welcome** — follow interface spec, add to `plugins/`
- **Core stays stable** — plugin system means community can extend without forking core

---

*This PRD is a draft. Once approved, implementation begins from Phase 1.*
