# PRD — Trade Agent

> AI-powered automated trading agent. LLM analyzes market data, news sentiment, and technical indicators to make informed trading decisions across multiple exchanges.

**Status:** Draft — pending approval
**Author:** mocasus
**License:** MIT

---

## 1. Problem

Existing trading bots are either:
- **Rule-based** (fixed strategies, can't adapt to changing market conditions)
- **SaaS lock-in** (no code visibility, monthly fees, your money on their keys)
- **Over-engineered** (thousands of lines, 20+ dependencies, impossible to audit)

There's no simple, open-source trading agent where an LLM actually **reasons** about market state and makes execution decisions — not just "if RSI < 30 then buy".

## 2. What This Is

A Python trading agent that uses LLMs (any OpenAI-compatible model) to:
1. Pull market data (price, volume, technical indicators) from exchanges
2. Scrape/ingest news and social sentiment
3. Feed everything to an LLM with a structured prompt
4. Parse the LLM's decision (BUY / SELL / HOLD) with reasoning
5. Execute the trade via exchange API
6. Report to Telegram

**What it's NOT:**
- Not a HFT / arbitrage bot (latency is in seconds, not microseconds)
- Not a "guaranteed profit" system (trading is risky, this is a tool)
- Not a SaaS (self-hosted, your keys, your money)

## 3. Target Users

- Developers who want AI-assisted trading without SaaS lock-in
- Traders who want to backtest AI strategies on historical data
- Tinkerers who want to experiment with LLM-driven financial analysis
- People who already run a VPS and want a trading bot as a systemd service

## 4. Core Features

### 4.1 Market Data
- Exchange REST API integration (Binance, Bybit — start with 2, expand later)
- Real-time price, order book depth, 24h volume
- Technical indicators: RSI, MACD, EMA, Bollinger Bands (computed locally, no paid TA API)
- Candle data: 1m, 5m, 15m, 1h, 4h, 1d

### 4.2 AI Decision Engine
- Structured prompt: market context + indicators + recent news → decision
- LLM output: JSON `{action, asset, amount_pct, reasoning, confidence}`
- Action types: `BUY`, `SELL`, `HOLD`, `CLOSE_ALL`
- Confidence score (0-100): below threshold → skip execution
- Multi-model support: any OpenAI-compatible endpoint (local llama, cloud API)
- Reasoning log: every decision is stored with full context for audit

### 4.3 News & Sentiment
- RSS feed aggregation (CryptoSlate, CoinDesk, etc.)
- Optional: X/Twitter sentiment via API
- LLM summarizes relevant news and assigns sentiment score
- Sentiment injected into decision prompt as context

### 4.4 Risk Management
- **Position sizing**: max % of portfolio per trade (configurable)
- **Stop-loss**: auto-set on every position (ATR-based or fixed %)
- **Take-profit**: auto-set based on risk-reward ratio
- **Max open positions**: limit concurrent trades
- **Daily loss limit**: stop trading if daily P&L drops below threshold
- **Cooldown**: minimum time between trades per asset

### 4.5 Execution
- Exchange API: Binance (spot), Bybit (spot/futures)
- Order types: market, limit
- Slippage protection: max deviation from expected price
- Paper trading mode: simulate execution without real funds (default ON)

### 4.6 Portfolio & Reporting
- Real-time portfolio value (BTC + fiat + altcoins)
- Trade history with P&L per trade
- Daily summary report via Telegram
- Alert on: trade executed, stop-loss hit, daily loss limit reached
- Web dashboard (optional, minimal — or just Telegram)

### 4.7 Backtesting
- Historical data replay (exchange kline API)
- Run AI decision engine on historical candles
- Simulate execution with realistic slippage + fees
- Performance report: total return, win rate, Sharpe ratio, max drawdown

## 5. Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Data Layer  │────▶│  AI Engine   │────▶│  Execution  │
│              │     │              │     │             │
│ • Exchange   │     │ • LLM prompt │     │ • Order API │
│   API       │     │ • Indicators │     │ • Risk check│
│ • News RSS  │     │ • Sentiment  │     │ • Paper mode│
│ • OHLCV     │     │ • Decision   │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
                                               │
                    ┌──────────────┐           ▼
                    │   Storage    │     ┌─────────────┐
                    │              │     │  Telegram   │
                    │ • SQLite DB  │     │  Alerts     │
                    │ • Trade log  │     │             │
                    │ • Decisions  │     └─────────────┘
                    └──────────────┘
```

### Design Principles
- **Single process, single file** core loop (`agent.py`) — easy to audit, easy to kill
- **SQLite** for persistence (no Postgres, no Redis)
- **systemd service** for deployment (familiar, reliable)
- **Config in YAML** — no DB for config
- **Minimal deps**: `requests`, `ccxt` or exchange SDK, `pyyaml`, `openai` (or `httpx`)

## 6. Project Structure

```
trade-agent/
├── agent.py              # Main loop: fetch data → AI decision → execute
├── exchange.py           # Exchange API wrapper (Binance, Bybit)
├── indicators.py         # Technical indicators (RSI, MACD, EMA, BB)
├── news.py               # RSS fetcher + sentiment prep
├── risk.py               # Position sizing, stop-loss, daily limits
├── backtest.py           # Historical replay engine
├── telegram_alert.py     # Telegram bot for alerts + commands
├── config.example.yaml   # Example configuration
├── requirements.txt      # Minimal dependencies
├── PRD.md                # This document
├── README.md             # Setup guide (ID/EN toggle)
└── LICENSE               # MIT
```

**8 files. No framework. No plugin system. No abstraction layers.**

## 7. Configuration

```yaml
# config.yaml
exchange:
  name: binance          # or bybit
  api_key: "..."
  api_secret: "..."
  testnet: true           # start with testnet

ai:
  base_url: "https://api.openai.com/v1"
  api_key: "..."
  model: "gpt-4o-mini"
  # or local: "http://localhost:8080/v1" with llama.cpp

trading:
  symbols: ["BTCUSDT", "ETHUSDT"]
  timeframe: "15m"       # candle interval
  paper_mode: true       # simulate trades (default ON)
  max_positions: 3
  max_position_pct: 10   # max 10% of portfolio per trade
  daily_loss_limit_pct: 5  # stop if daily loss > 5%
  confidence_threshold: 65  # min confidence to execute (0-100)
  cooldown_minutes: 30   # min time between trades per symbol

risk:
  stop_loss_pct: 2       # auto stop-loss at 2% below entry
  take_profit_rr: 2      # take-profit at 2x risk (RR 1:2)

news:
  enabled: true
  feeds:
    - "https://cryptoslate.com/feed/"
    - "https://www.coindesk.com/arc/outboundfeeds/rss/"

telegram:
  bot_token: "..."
  chat_id: 123456789
  alerts: [trade, stop_loss, daily_report]

schedule:
  interval_minutes: 15   # run every 15 minutes
```

## 8. Decision Prompt (Core)

```
You are a trading analyst. Analyze the following market data and make a decision.

## Market: BTCUSDT (15m timeframe)
Current price: $43,250
24h change: +2.3%
Volume: $1.2B

## Indicators
RSI (14): 32.1  [approaching oversold]
MACD: -45.2 (below signal line)
EMA 20: $43,800  [price below EMA]
EMA 50: $44,100
Bollinger Bands: Lower $42,900 | Mid $43,500 | Upper $44,100

## Recent News (last 2h)
1. "BlackRock files for spot Ethereum ETF" — positive sentiment
2. "SEC delays decision on Bitcoin ETF" — neutral

## Current Portfolio
Available USDT: $5,000
Open positions: 1 (ETHUSDT, entry $2,250, current +1.2%)

## Decision
Respond as JSON:
{
  "action": "BUY" | "SELL" | "HOLD" | "CLOSE_ALL",
  "symbol": "BTCUSDT",
  "amount_pct": 5,        // % of available capital
  "confidence": 75,       // 0-100
  "reasoning": "Brief explanation of your analysis"
}
```

## 9. Roadmap

### Phase 1 — MVP (v0.1)
- [ ] Exchange API integration (Binance spot, paper mode)
- [ ] Technical indicators (RSI, MACD, EMA, BB)
- [ ] AI decision engine (single LLM, structured JSON output)
- [ ] Basic risk management (stop-loss, position sizing)
- [ ] SQLite trade log
- [ ] Telegram alerts (trade executed, daily summary)
- [ ] systemd service template

### Phase 2 — News + Backtest (v0.2)
- [ ] RSS news aggregation + sentiment
- [ ] Backtesting engine (historical replay)
- [ ] Performance metrics (Sharpe, drawdown, win rate)
- [ ] Multi-symbol support

### Phase 3 — Multi-exchange + Futures (v0.3)
- [ ] Bybit integration
- [ ] Futures support (leverage, funding rate)
- [ ] Advanced risk management (trailing stop, OCO orders)

### Phase 4 — Community (v0.4+)
- [ ] Plugin-free strategy customization (config-driven)
- [ ] Web dashboard (minimal, read-only)
- [ ] Multi-language README (ID/EN)
- [ ] Docker image

## 10. Non-Goals

- **Not a copy-trading platform** — this trades its own AI decisions, not mirroring others
- **Not an exchange** — no order matching, no custody
- **Not financial advice** — this is a tool, users are responsible for their own money
- **Not HFT** — decisions take seconds, not microseconds
- **No web framework** — Telegram is the primary interface, optional minimal dashboard later
- **No plugin system** — configuration-driven customization, not code extensions

## 11. Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Standard for trading/AI, ccxt ecosystem |
| Exchange API | `ccxt` | Unified API for 100+ exchanges, well-maintained |
| LLM Client | `openai` SDK | Works with any OpenAI-compatible endpoint |
| Indicators | `pandas-ta` or manual | Lightweight, no heavy framework |
| Storage | SQLite (`sqlite3`) | Zero-config, single file, sufficient for this scale |
| Config | YAML (`pyyaml`) | Human-readable, familiar |
| Alerts | `python-telegram-bot` or raw `requests` | Telegram is the UI |
| Scheduling | `systemd` timer or `apscheduler` | No cron, no celery |

**Total dependencies: ~5-6 packages. No web framework, no ORM, no message queue.**

## 12. Safety

- **Paper mode ON by default** — new users start simulated
- **Testnet first** — exchange testnet before mainnet
- **No leverage by default** — spot only in Phase 1
- **Daily loss limit** — hard stop, can't be overridden by AI
- **Max position size** — AI can't exceed configured %
- **Kill switch** — Telegram command `/stop` halts the agent immediately
- **Audit trail** — every AI decision logged with full context + reasoning

## 13. Open Source Considerations

- **License:** MIT (max permissive)
- **No API keys in repo** — `.env` + `.gitignore`
- **No AI/agent credits** — clean authorship (per user preference)
- **README:** 🇮🇩/🇬🇧 toggle with `<details>` tags
- **Logo:** 2-3 color geometric, no text (Stripe/Vercel style)
- **Version badge** in README header + footer
- **Contributions welcome** but keep the "8 files, no framework" constraint

---

*This PRD is a draft. Once approved, implementation begins from Phase 1 MVP.*
