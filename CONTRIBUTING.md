# Contributing to trade-agent

Thanks for your interest! This project welcomes contributions — bug fixes, new plugins, docs improvements, and refactors. Keep things **simple, modular, and testable**.

---

## 🚀 Quick Start

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/trade-agent.git
cd trade-agent
pip install -e ".[all]"
pre-commit install   # optional but recommended

# Make changes...
ruff check . && ruff format .
pytest

# Commit + push + open PR
```

---

## 🧩 Plugin Development

The most welcomed contributions are **new plugins** for the 6 slots:

- **data_source** — wrap a new market data API
- **strategy** — implement a new decision algorithm
- **exchange** — add support for a new exchange
- **notifier** — output to Slack, email, SMS, etc.
- **sentiment** — wrap a new sentiment source (Twitter, news, on-chain)
- **risk_profile** — implement a new sizing/stop strategy

### Plugin contract

Every plugin lives under `trade_agent/plugins/<slot>/<your_name>.py` and exposes a class implementing the base protocol:

```python
from trade_agent.plugins.strategy import StrategyBase

class MyStrategy(StrategyBase):
    name = "my_strategy"

    def decide(self, ctx: TradeContext) -> Decision:
        # your logic
        return Decision(action="buy", confidence=0.8)
```

Add a test under `tests/test_<your_plugin>.py`. Coverage should not drop below 100% on critical paths.

---

## 📐 Code Style

- **Ruff** is the single source of truth — `ruff check . && ruff format .` before every commit
- **Type hints required** on public APIs (private helpers can skip)
- **No mutable defaults** in function signatures
- **Async-first** — use `asyncio` for I/O
- Line length: **100 chars** (configured in `pyproject.toml`)

---

## ✅ Tests

- All PRs must pass `pytest` — 39 tests at 100% on critical paths today
- Add at least one happy-path + one error-case test per new plugin
- Use `tests/conftest.py` fixtures where possible — don't reinvent

```bash
pytest                      # all tests
pytest tests/test_risk.py   # single file
pytest -k llm               # by keyword
pytest --cov=trade_agent    # with coverage
```

---

## 📝 Commit Style

Conventional Commits format (enforced for clean changelog generation):

```
feat(strategy): add MACD crossover plugin
fix(risk): correct kelly fraction for negative edge
docs(readme): add backtest example
chore(deps): bump ccxt to 4.5
test(storage): add migration round-trip test
refactor(loader): simplify plugin discovery
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`.

---

## 🔀 PR Workflow

1. **Fork** + create a feature branch (`feat/macd-strategy` or `fix/kelly-edge`)
2. **One PR = one concern** — don't bundle unrelated changes
3. **CI must pass** — ruff + pytest
4. **Update CHANGELOG.md** under `## [Unreleased]` (create the section if missing)
5. **Add yourself** to a contributors list if you want credit (optional)
6. **Be patient** — maintainer review may take a few days

---

## 🐛 Reporting Bugs

Open an [issue](https://github.com/mocasus/trade-agent/issues/new) with:

- **What you expected** vs **what happened**
- **Minimal reproduction** — config snippet + command
- **Environment** — OS, Python version, `pip list | grep -E 'ccxt|pydantic|trade-agent'`
- **Logs** — paste relevant traceback / log lines

---

## 🛡️ Security

Found a vulnerability? **Do not open a public issue.** See [SECURITY.md](SECURITY.md) for the disclosure process.

---

## 📜 License

By contributing, you agree your work will be released under the project's [MIT License](LICENSE).
