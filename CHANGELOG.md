# Changelog

All notable changes to **trade-agent** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-06-30

First stable release. Modular AI trading agent with full plugin system, paper-mode safety default, and 39 passing tests at 100% coverage.

### Added — Core Engine
- 🧠 **LLM-driven decision loop** — market data + news + indicators → analyzed by LLM → trade decision
- 🧩 **6-slot plugin system**:
  - `data_source` — `ccxt` (100+ exchanges), `csv` (backtesting)
  - `strategy` — `llm`, `rule`, `partial_exit`, `rule_builder`
  - `exchange` — `ccxt`, `paper` (default), `bybit_futures`
  - `notifier` — `telegram`, `discord`, `webhook`, `console`
  - `sentiment` — `rss_llm`, `none`
  - `risk_profile` — `conservative`, `moderate`, `aggressive`, `trailing_stop`, `kelly_sizing`
- 🛡️ **Paper mode default** — zero accidental real-money trades
- 🔒 **Risk guards** — max position size, daily loss cap, circuit breakers
- 📊 **Storage layer** — SQLite trade journal, portfolio state, decision log

### Added — Quality
- ✅ **39 passing tests** across 7 test modules ([TESTS.md](TESTS.md))
- 📐 **100% coverage** on critical paths (config, models, risk, storage, plugin loader, phases 3-4)
- 🦀 **Ruff** for linting + formatting (no Black, no isort — single tool)
- 🐳 **Dockerfile + docker-compose** ready for VPS deployment

### Added — Docs
- 📖 **README.md** — bilingual (Bahasa Indonesia + English), 13.8KB comprehensive
- 📋 **TESTS.md** — full test breakdown
- ⚙️ **config.example.yaml** — annotated configuration template
- 📦 **systemd unit** for VPS service install

### Architecture
- **No framework lock-in** — plain Python + plugin discovery via entry points
- **Every component swappable** — bring your own data source, strategy, exchange
- **Async-first** — `asyncio` throughout for concurrent exchange/news polling
- **Pydantic models** — type-safe config + trade objects

### Stats
- **3,722 LOC** (Python 72.5%, Shell 25.1%, HTML/Docker 2.4%)
- **151 KB** repo size
- **MIT License**

---

## Template for future entries

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- New features or plugins

### Changed
- Modifications to existing behavior

### Deprecated
- Soon-to-be-removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Vulnerability patches
```
