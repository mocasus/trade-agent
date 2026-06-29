#!/bin/bash
set -e
cd /root/trade-agent

echo "=== Phase 3: Trailing Stop ==="
python3 << 'PYEOF'
code = '''"""Trailing stop-loss risk profile."""
from __future__ import annotations
from typing import Any
from trade_agent.interfaces import RiskProfileInterface
from trade_agent.models import Decision, MarketContext, Position

class TrailingStopProfile(RiskProfileInterface):
    """Trailing stop that moves up with price, never down."""

    def __init__(self, trail_percent: float = 2.0, activation_threshold: float = 1.0):
        self.trail_percent = trail_percent
        self.activation_threshold = activation_threshold
        self._highest_price: dict[str, float] = {}

    def calculate_position_size(self, balance: float, price: float, confidence: float) -> float:
        max_pct = 0.05 * confidence
        return balance * max_pct / price

    def check_risk(self, decision: Decision, context: MarketContext, positions: list[Position]) -> Decision:
        symbol = decision.symbol
        current_price = context.ticker.last_price if context.ticker else 0
        entry_price = positions[0].entry_price if positions else current_price

        # Track highest price
        if symbol not in self._highest_price:
            self._highest_price[symbol] = current_price
        self._highest_price[symbol] = max(self._highest_price[symbol], current_price)

        # Only activate trailing stop after activation_threshold profit
        profit_pct = (current_price - entry_price) / entry_price * 100
        if profit_pct < self.activation_threshold:
            return decision

        # Trail from highest price
        highest = self._highest_price[symbol]
        trail_stop = highest * (1 - self.trail_percent / 100)

        if current_price <= trail_stop:
            decision.action = "sell"
            decision.confidence *= 0.9
            decision.reason = f"Trailing stop hit: price {current_price:.2f} <= trail {trail_stop:.2f} (trail_pct={self.trail_percent}%, high={highest:.2f})"

        return decision

    def calculate_stop_loss(self, entry_price: float, atr: float = 0) -> float:
        return entry_price * (1 - self.trail_percent / 100)
'''
with open('trade_agent/plugins/risk_profile/trailing_stop.py', 'w') as f:
    f.write(code)
print("OK")
PYEOF

echo "=== Phase 3: Kelly Criterion ==="
python3 << 'PYEOF'
code = '''"""Kelly criterion position sizing risk profile."""
from __future__ import annotations
from typing import Any
from trade_agent.interfaces import RiskProfileInterface
from trade_agent.models import Decision, MarketContext, Position

class KellyCriterionProfile(RiskProfileInterface):
    """Kelly criterion with fractional safety: f = fraction * (bp - q) / b."""

    def __init__(self, fraction: float = 0.5, min_samples: int = 10,
                 default_win_rate: float = 0.55, default_win_loss_ratio: float = 1.5):
        self.fraction = fraction
        self.min_samples = min_samples
        self.default_win_rate = default_win_rate
        self.default_win_loss_ratio = default_win_loss_ratio
        self._wins = 0
        self._losses = 0
        self._total_win = 0.0
        self._total_loss = 0.0

    def _win_rate(self) -> float:
        total = self._wins + self._losses
        if total < self.min_samples:
            return self.default_win_rate
        return self._wins / total

    def _win_loss_ratio(self) -> float:
        if self._losses == 0 or self._total_loss == 0:
            return self.default_win_loss_ratio
        avg_win = self._total_win / self._wins if self._wins else 0
        avg_loss = self._total_loss / self._losses if self._losses else 0
        if avg_loss == 0:
            return self.default_win_loss_ratio
        return avg_win / avg_loss

    def calculate_position_size(self, balance: float, price: float, confidence: float) -> float:
        p = self._win_rate()
        b = self._win_loss_ratio()
        q = 1 - p
        kelly = (b * p - q) / b
        kelly = max(0, kelly)  # never negative
        sized = self.fraction * kelly
        sized *= confidence  # scale with confidence
        sized = min(sized, 0.25)  # cap at 25% of balance
        return balance * sized / price

    def check_risk(self, decision: Decision, context: MarketContext, positions: list[Position]) -> Decision:
        return decision

    def calculate_stop_loss(self, entry_price: float, atr: float = 0) -> float:
        if atr > 0:
            return entry_price - 2 * atr
        return entry_price * 0.95

    def record_trade(self, pnl: float) -> None:
        if pnl > 0:
            self._wins += 1
            self._total_win += pnl
        elif pnl < 0:
            self._losses += 1
            self._total_loss += abs(pnl)
'''
with open('trade_agent/plugins/risk_profile/kelly_sizing.py', 'w') as f:
    f.write(code)
print("OK")
PYEOF

echo "=== Phase 3: Bybit Futures ==="
python3 << 'PYEOF'
code = '''"""Bybit futures exchange adapter."""
from __future__ import annotations
from typing import Any
from trade_agent.interfaces import ExchangeInterface
from trade_agent.models import Order, Position, Balance

class BybitFuturesExchange(ExchangeInterface):
    """Bybit USDT perpetual futures via ccxt."""

    def __init__(self, api_key: str = "", secret: str = "",
                 leverage: int = 10, margin_mode: str = "cross",
                 position_mode: str = "one-way", testnet: bool = False):
        import ccxt
        self.exchange = ccxt.bybit({
            "apiKey": api_key, "secret": secret,
            "options": {"defaultType": "swap"},
        })
        if testnet:
            self.exchange.set_sandbox_mode(True)
        self.leverage = leverage
        self.margin_mode = margin_mode
        self._position_mode_set = position_mode == "one-way"

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        return self.exchange.set_leverage(leverage, symbol)

    def set_margin_mode(self, symbol: str, mode: str) -> dict:
        return self.exchange.set_margin_mode(mode, symbol)

    def get_balance(self) -> Balance:
        bal = self.exchange.fetch_balance({"type": "swap"})
        free = float(bal.get("free", {}).get("USDT", 0))
        used = float(bal.get("used", {}).get("USDT", 0))
        total = float(bal.get("total", {}).get("USDT", 0))
        return Balance(asset="USDT", free=free, used=used, total=total)

    def get_positions(self, symbols: list[str] | None = None) -> list[Position]:
        positions = []
        for sym in (symbols or []):
            pos = self.exchange.fetch_positions([sym])
            for p in pos:
                if float(p.get("contracts", 0)) > 0:
                    positions.append(Position(
                        symbol=p["symbol"], side=p["side"],
                        entry_price=float(p["entryPrice"]),
                        quantity=float(p["contracts"]),
                        unrealized_pnl=float(p.get("unrealizedPnl", 0)),
                        leverage=int(p.get("leverage", self.leverage)),
                    ))
        return positions

    def place_order(self, symbol: str, side: str, quantity: float,
                    order_type: str = "market", price: float | None = None,
                    params: dict | None = None) -> Order:
        p = params or {}
        p["leverage"] = self.leverage
        result = self.exchange.create_order(symbol, order_type, side, quantity, price or 0, p)
        return Order(
            order_id=result["id"], symbol=result["symbol"],
            side=result["side"], order_type=result["type"],
            quantity=float(result["amount"]), price=float(result.get("price", 0) or 0),
            status=result["status"], timestamp=result["timestamp"],
        )

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        self.exchange.cancel_order(order_id, symbol)
        return True

    def get_order(self, order_id: str, symbol: str) -> Order:
        o = self.exchange.fetch_order(order_id, symbol)
        return Order(order_id=o["id"], symbol=o["symbol"], side=o["side"],
                     order_type=o["type"], quantity=float(o["amount"]),
                     price=float(o.get("price", 0) or 0), status=o["status"],
                     timestamp=o["timestamp"])

    def get_ticker(self, symbol: str) -> dict:
        return self.exchange.fetch_ticker(symbol)
'''
with open('trade_agent/plugins/exchange/bybit_futures.py', 'w') as f:
    f.write(code)
print("OK")
PYEOF

echo "=== Phase 3: Partial Exit Strategy ==="
python3 << 'PYEOF'
code = '''"""Partial exit strategy — scale out in increments."""
from __future__ import annotations
from typing import Any
from trade_agent.interfaces import StrategyInterface
from trade_agent.models import Candle, Decision, MarketContext, Position, SentimentScore

class PartialExitStrategy(StrategyInterface):
    """Exit positions in stages: 25% at +5%, 25% at +10%, rest rides."""

    def __init__(self, levels: list[dict] | None = None):
        self.levels = levels or [
            {"pct_gain": 5.0, "exit_pct": 25, "action": "partial_exit"},
            {"pct_gain": 10.0, "exit_pct": 25, "action": "partial_exit"},
            {"pct_gain": 15.0, "exit_pct": 50, "action": "sell"},
        ]
        self._triggered: dict[str, set[int]] = {}

    def analyze(self, candles: list[Candle], context: MarketContext,
                sentiment: SentimentScore | None = None) -> Decision:
        if not context.ticker or not context.positions:
            return Decision(symbol="", action="hold", confidence=0)

        symbol = context.positions[0].symbol
        entry = context.positions[0].entry_price
        current = context.ticker.last_price
        gain_pct = (current - entry) / entry * 100

        triggered = self._triggered.setdefault(symbol, set())

        for i, level in enumerate(self.levels):
            if i in triggered:
                continue
            if gain_pct >= level["pct_gain"]:
                triggered.add(i)
                return Decision(
                    symbol=symbol,
                    action=level["action"],
                    confidence=0.8,
                    quantity=context.positions[0].quantity * level["exit_pct"] / 100,
                    reason=f"Partial exit: {level['exit_pct']}% at +{level['pct_gain']}% gain (current +{gain_pct:.1f}%)",
                    order_type="partial_exit",
                )

        return Decision(symbol=symbol, action="hold", confidence=0.3,
                        reason=f"Gain {gain_pct:.1f}% — no exit level triggered yet")
'''
with open('trade_agent/plugins/strategy/partial_exit.py', 'w') as f:
    f.write(code)
print("OK")
PYEOF

echo "=== Phase 3: Models update (OCO + PartialExit) ==="
python3 << 'PYEOF'
import re

with open('trade_agent/models.py', 'r') as f:
    content = f.read()

# Add OCOOrder and PartialExit models before the last closing
oco_model = '''

class OCOOrder:
    """One-Cancels-Other order: stop + limit linked."""
    def __init__(self, symbol: str, side: str, quantity: float,
                 stop_price: float, limit_price: float,
                 order_id: str = "", linked_order_id: str = ""):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.stop_price = stop_price
        self.limit_price = limit_price
        self.order_id = order_id
        self.linked_order_id = linked_order_id

class PartialExit:
    """Partial position exit with remaining quantity tracking."""
    def __init__(self, position_id: str, exit_percentage: float,
                 exit_price: float, remaining_quantity: float):
        self.position_id = position_id
        self.exit_percentage = exit_percentage
        self.exit_price = exit_price
        self.remaining_quantity = remaining_quantity
'''

# Find where Order class ends and append
if 'class OCOOrder' not in content:
    content += oco_model
    with open('trade_agent/models.py', 'w') as f:
        f.write(content)
    print("OK")
else:
    print("SKIP - already exists")
PYEOF

echo "=== Phase 3: Config update ==="
python3 << 'PYEOF'
import yaml

with open('config.example.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Add trailing_stop section
config.setdefault('risk', {})
config['risk']['trailing_stop'] = {
    'trail_percent': 2.0,
    'activation_threshold': 1.0,
    'description': 'Trailing stop-loss that moves up with price'
}

# Add kelly criterion section
config['risk']['kelly'] = {
    'fraction': 0.5,
    'min_samples': 10,
    'default_win_rate': 0.55,
    'description': 'Fractional Kelly criterion for position sizing'
}

# Add bybit futures section
config.setdefault('exchange', {})
config['exchange']['bybit_futures'] = {
    'leverage': 10,
    'margin_mode': 'cross',
    'position_mode': 'one-way',
    'testnet': False,
    'description': 'Bybit USDT perpetual futures'
}

# Add partial exit levels to strategy
config.setdefault('strategy', {})
config['strategy']['partial_exit_levels'] = [
    {'pct_gain': 5.0, 'exit_pct': 25},
    {'pct_gain': 10.0, 'exit_pct': 25},
    {'pct_gain': 15.0, 'exit_pct': 50},
]

with open('config.example.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
print("OK")
PYEOF

echo "=== Phase 4: Dashboard ==="
mkdir -p trade_agent/dashboard

python3 << 'PYEOF'
code = '''"""Minimal read-only HTTP dashboard."""
from __future__ import annotations
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from trade_agent.storage import Storage

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "templates")

class DashboardHandler(BaseHTTPRequestHandler):
    storage: Storage | None = None

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_file("index.html", "text/html")
        elif self.path == "/api/status":
            self._serve_json(self._status())
        elif self.path == "/api/trades":
            self._serve_json(self._trades())
        elif self.path == "/api/positions":
            self._serve_json(self._positions())
        elif self.path == "/api/pnl":
            self._serve_json(self._pnl())
        else:
            self.send_error(404)

    def _serve_file(self, name: str, mime: str):
        path = os.path.join(DASHBOARD_DIR, name)
        if os.path.exists(path):
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.end_headers()
            with open(path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

    def _serve_json(self, data: dict):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _status(self) -> dict:
        if not self.storage:
            return {"error": "storage not configured"}
        trades = self.storage.get_trades(limit=100)
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        return {"total_trades": len(trades), "total_pnl": total_pnl,
                "win_rate": win_rate, "status": "running"}

    def _trades(self) -> dict:
        if not self.storage:
            return {"trades": []}
        return {"trades": self.storage.get_trades(limit=50)}

    def _positions(self) -> dict:
        if not self.storage:
            return {"positions": []}
        return {"positions": self.storage.get_positions()}

    def _pnl(self) -> dict:
        if not self.storage:
            return {"daily": []}
        return {"daily": self.storage.get_daily_pnl()}

    def log_message(self, format, *args):
        pass  # suppress logs


def run_dashboard(storage: Storage, port: int = 8080):
    DashboardHandler.storage = storage
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"Dashboard running on http://0.0.0.0:{port}")
    server.serve_forever()
'''
with open('trade_agent/dashboard/server.py', 'w') as f:
    f.write(code)
print("OK")
PYEOF

echo "=== Phase 4: Dashboard HTML ==="
python3 << 'PYEOF'
html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trade Agent Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #1a1a2e; color: #eee; font-family: -apple-system, monospace; }
.header { background: #16213e; padding: 1rem 2rem; border-bottom: 2px solid #e94560; }
.header h1 { color: #e94560; font-size: 1.4rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; padding: 1rem 2rem; }
.card { background: #16213e; border-radius: 8px; padding: 1.2rem; border: 1px solid #0f3460; }
.card h2 { color: #e94560; font-size: 0.9rem; margin-bottom: 0.8rem; letter-spacing: 1px; }
.stat { display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid #0f3460; }
.stat-label { color: #888; font-size: 0.8rem; }
.stat-value { color: #eee; font-size: 0.9rem; font-weight: bold; }
.positive { color: #4ecca3; }
.negative { color: #e94560; }
table { width: 100%; border-collapse: collapse; font-size: 0.75rem; }
th { color: #888; text-align: left; padding: 0.5rem; border-bottom: 1px solid #0f3460; }
td { padding: 0.4rem 0.5rem; }
canvas { width: 100%; height: 200px; }
</style>
</head>
<body>
<div class="header"><h1>Trade Agent</h1></div>
<div class="grid">
  <div class="card"><h2>PORTFOLIO</h2>
    <div id="portfolio"><div class="stat"><span class="stat-label">Total PnL</span><span class="stat-value" id="total-pnl">--</span></div>
    <div class="stat"><span class="stat-label">Win Rate</span><span class="stat-value" id="win-rate">--</span></div>
    <div class="stat"><span class="stat-label">Total Trades</span><span class="stat-value" id="total-trades">--</span></div>
    <div class="stat"><span class="stat-label">Status</span><span class="stat-value" id="status">--</span></div></div>
  </div>
  <div class="card"><h2>DAILY PNL</h2><canvas id="pnl-chart"></canvas></div>
  <div class="card"><h2>POSITIONS</h2><table id="pos-table"><thead><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>PnL</th></tr></thead><tbody></tbody></table></div>
  <div class="card"><h2>RECENT TRADES</h2><table id="trade-table"><thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>PnL</th></tr></thead><tbody></tbody></table></div>
</div>
<script>
async function refresh() {
  try {
    const status = await fetch("/api/status").then(r => r.json());
    document.getElementById("total-pnl").textContent = "$" + (status.total_pnl || 0).toFixed(2);
    document.getElementById("total-pnl").className = "stat-value " + (status.total_pnl >= 0 ? "positive" : "negative");
    document.getElementById("win-rate").textContent = (status.win_rate || 0).toFixed(1) + "%";
    document.getElementById("total-trades").textContent = status.total_trades || 0;
    document.getElementById("status").textContent = status.status || "--";
  } catch(e) {}

  try {
    const positions = await fetch("/api/positions").then(r => r.json());
    const tbody = document.querySelector("#pos-table tbody");
    tbody.innerHTML = "";
    (positions.positions || []).forEach(p => {
      const cls = p.unrealized_pnl >= 0 ? "positive" : "negative";
      tbody.innerHTML += `<tr><td>${p.symbol}</td><td>${p.side}</td><td>${p.quantity}</td><td>${p.entry_price}</td><td class="${cls}">${p.unrealized_pnl}</td></tr>`;
    });
  } catch(e) {}

  try {
    const trades = await fetch("/api/trades").then(r => r.json());
    const tbody = document.querySelector("#trade-table tbody");
    tbody.innerHTML = "";
    (trades.trades || []).slice(0, 20).forEach(t => {
      const cls = (t.pnl || 0) >= 0 ? "positive" : "negative";
      tbody.innerHTML += `<tr><td>${t.timestamp || ""}</td><td>${t.symbol}</td><td>${t.side}</td><td>${t.quantity}</td><td class="${cls}">${(t.pnl || 0).toFixed(2)}</td></tr>`;
    });
  } catch(e) {}
}
refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>'''
with open('trade_agent/dashboard/templates/index.html', 'w') as f:
    f.write(html)
print("OK")
PYEOF

echo "=== Phase 4: Rule Builder ==="
python3 << 'PYEOF'
code = '''"""Config-driven rule-based strategy builder."""
from __future__ import annotations
from typing import Any
from trade_agent.interfaces import StrategyInterface
from trade_agent.models import Candle, Decision, MarketContext, Position, SentimentScore

class RuleBuilderStrategy(StrategyInterface):
    """Build strategy purely from YAML config rules. No code needed."""

    CONDITIONS = {
        "price_above": lambda c, t, v: t.last_price > v,
        "price_below": lambda c, t, v: t.last_price < v,
        "rsi_above": lambda c, t, v: _calc_rsi(c) > v,
        "rsi_below": lambda c, t, v: _calc_rsi(c) < v,
        "volume_above": lambda c, t, v: t.volume > v,
        "ema_cross": lambda c, t, v: _ema_cross(c, v),
        "macd_signal": lambda c, t, v: _macd_signal(c, v),
    }

    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules or []

    def analyze(self, candles: list[Candle], context: MarketContext,
                sentiment: SentimentScore | None = None) -> Decision:
        if not context.ticker or not candles:
            return Decision(symbol="", action="hold", confidence=0)

        total_confidence = 0.0
        best_action = "hold"
        best_reason = "No rules triggered"

        for rule in self.rules:
            signal = rule.get("signal", "")
            condition = rule.get("condition", "")
            threshold = rule.get("threshold", 0)
            action = rule.get("action", "hold")
            weight = rule.get("confidence_weight", 1.0)

            check_fn = self.CONDITIONS.get(condition)
            if check_fn and check_fn(candles, context.ticker, threshold):
                total_confidence += weight
                best_action = action
                best_reason = f"Rule triggered: {signal} {condition} {threshold}"

        return Decision(
            symbol=context.ticker.symbol,
            action=best_action,
            confidence=min(total_confidence, 1.0),
            reason=best_reason,
        )


def _calc_rsi(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 50.0
    closes = [c.close for c in candles[-(period + 1):]]
    gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _ema(prices: list[float], period: int) -> float:
    if not prices:
        return 0
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def _ema_cross(candles: list[Candle], short_period: int) -> bool:
    closes = [c.close for c in candles]
    if len(closes) < short_period * 2:
        return False
    short_ema = _ema(closes[-short_period:], short_period)
    long_ema = _ema(closes[-(short_period * 2):], short_period * 2)
    prev_short = _ema(closes[-(short_period + 1):-1], short_period)
    prev_long = _ema(closes[-(short_period * 2 + 1):-1], short_period * 2)
    return prev_short <= prev_long and short_ema > long_ema


def _macd_signal(candles: list[Candle], signal_period: int) -> bool:
    closes = [c.close for c in candles]
    if len(closes) < 26:
        return False
    macd = _ema(closes[-12:], 12) - _ema(closes[-26:], 26)
    signal = _ema([closes[-(26 + i):-(i or None)] for i in range(9)], 9)
    return macd > signal
'''
with open('trade_agent/plugins/strategy/rule_builder.py', 'w') as f:
    f.write(code)
print("OK")
PYEOF

echo "=== Phase 4: Docker Compose ==="
cat > docker-compose.yml << 'YAML'
version: "3.8"
services:
  trade-agent:
    build: .
    env_file: .env
    volumes:
      - trade-data:/app/data
      - ./config.yaml:/app/config.yaml:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://dashboard:8080/api/status')"]
      interval: 60s
      timeout: 10s
      retries: 3

  dashboard:
    build: .
    command: ["python3", "-m", "trade_agent.dashboard.server"]
    ports:
      - "8080:8080"
    env_file: .env
    volumes:
      - trade-data:/app/data:ro
      - ./config.yaml:/app/config.yaml:ro
    restart: unless-stopped

volumes:
  trade-data:
YAML

echo "=== Phase 4: Config update ==="
python3 << 'PYEOF'
import yaml

with open('config.example.yaml', 'r') as f:
    config = yaml.safe_load(f)

config['dashboard'] = {
    'port': 8080,
    'theme': 'dark',
    'description': 'Read-only web dashboard'
}

config['strategy']['rule_builder'] = {
    'description': 'Config-driven rules, no code needed',
    'rules': [
        {'signal': 'btc_price', 'condition': 'price_above', 'threshold': 50000, 'action': 'sell', 'confidence_weight': 0.7},
        {'signal': 'btc_rsi', 'condition': 'rsi_below', 'threshold': 30, 'action': 'buy', 'confidence_weight': 0.6},
        {'signal': 'btc_ema', 'condition': 'ema_cross', 'threshold': 12, 'action': 'buy', 'confidence_weight': 0.5},
    ]
}

with open('config.example.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
print("OK")
PYEOF

echo "=== Phase 3+4 Tests ==="
cat > tests/test_phase3.py << 'PYEOF'
"""Tests for Phase 3 features."""
from trade_agent.plugins.risk_profile.trailing_stop import TrailingStopProfile
from trade_agent.plugins.risk_profile.kelly_sizing import KellyCriterionProfile
from trade_agent.plugins.strategy.partial_exit import PartialExitStrategy
from trade_agent.models import OCOOrder, PartialExit, Decision, MarketContext, Position, Ticker, Candle

def test_trailing_stop_calc():
    ts = TrailingStopProfile(trail_percent=2.0, activation_threshold=1.0)
    stop = ts.calculate_stop_loss(100.0)
    assert stop == 98.0

def test_trailing_stop_not_activated():
    ts = TrailingStopProfile(trail_percent=2.0, activation_threshold=5.0)
    dec = Decision(symbol="BTC", action="buy", confidence=0.8, entry_price=100)
    ctx = MarketContext(ticker=Ticker(symbol="BTC", last_price=101, volume=1000), positions=[])
    result = ts.check_risk(dec, ctx, [])
    assert result.action == "buy"  # not activated yet, only 1% gain < 5% threshold

def test_trailing_stop_hit():
    ts = TrailingStopProfile(trail_percent=2.0, activation_threshold=1.0)
    # Simulate price going up to 110, then dropping to trail stop
    ts._highest_price["BTC"] = 110.0
    dec = Decision(symbol="BTC", action="hold", confidence=0.8)
    pos = Position(symbol="BTC", side="long", entry_price=100, quantity=1)
    ctx = MarketContext(ticker=Ticker(symbol="BTC", last_price=107.7, volume=1000), positions=[pos])
    result = ts.check_risk(dec, ctx, [pos])
    assert result.action == "sell"  # 107.7 <= 110 * 0.98 = 107.8

def test_kelly_sizing_zero():
    k = KellyCriterionProfile(fraction=0.5, min_samples=10)
    size = k.calculate_position_size(10000, 100, 0.5)
    assert size > 0  # uses defaults when no history

def test_kelly_record():
    k = KellyCriterionProfile()
    k.record_trade(100)
    k.record_trade(-50)
    assert k._wins == 1
    assert k._losses == 1

def test_partial_exit_level1():
    pe = PartialExitStrategy()
    pos = Position(symbol="BTC", side="long", entry_price=100, quantity=1)
    ctx = MarketContext(ticker=Ticker(symbol="BTC", last_price=105, volume=1000), positions=[pos])
    dec = pe.analyze([], ctx)
    assert dec.action == "partial_exit"
    assert dec.quantity == 0.25

def test_partial_exit_no_trigger():
    pe = PartialExitStrategy()
    pos = Position(symbol="BTC", side="long", entry_price=100, quantity=1)
    ctx = MarketContext(ticker=Ticker(symbol="BTC", last_price=102, volume=1000), positions=[pos])
    dec = pe.analyze([], ctx)
    assert dec.action == "hold"

def test_oco_order():
    oco = OCOOrder(symbol="BTC", side="sell", quantity=1, stop_price=95, limit_price=110)
    assert oco.stop_price == 95
    assert oco.limit_price == 110

def test_partial_exit_model():
    pe = PartialExit(position_id="pos1", exit_percentage=25, exit_price=105, remaining_quantity=0.75)
    assert pe.exit_percentage == 25
    assert pe.remaining_quantity == 0.75
PYEOF

cat > tests/test_phase4.py << 'PYEOF'
"""Tests for Phase 4 features."""
from trade_agent.plugins.strategy.rule_builder import RuleBuilderStrategy
from trade_agent.models import Decision, MarketContext, Ticker, Candle

def test_rule_builder_price_above():
    rules = [{"signal": "test", "condition": "price_above", "threshold": 100, "action": "sell", "confidence_weight": 0.7}]
    rb = RuleBuilderStrategy(rules=rules)
    ctx = MarketContext(ticker=Ticker(symbol="BTC", last_price=105, volume=1000), positions=[])
    dec = rb.analyze([], ctx)
    assert dec.action == "sell"
    assert dec.confidence == 0.7

def test_rule_builder_no_trigger():
    rules = [{"signal": "test", "condition": "price_above", "threshold": 200, "action": "sell", "confidence_weight": 0.7}]
    rb = RuleBuilderStrategy(rules=rules)
    ctx = MarketContext(ticker=Ticker(symbol="BTC", last_price=105, volume=1000), positions=[])
    dec = rb.analyze([], ctx)
    assert dec.action == "hold"

def test_rule_builder_multiple():
    rules = [
        {"signal": "rsi_low", "condition": "rsi_below", "threshold": 30, "action": "buy", "confidence_weight": 0.6},
        {"signal": "price_low", "condition": "price_below", "threshold": 100, "action": "buy", "confidence_weight": 0.4},
    ]
    rb = RuleBuilderStrategy(rules=rules)
    ctx = MarketContext(ticker=Ticker(symbol="BTC", last_price=90, volume=1000), positions=[])
    # Short candles list to force default RSI=50 (>30, won't trigger rsi_below)
    candles = [Candle(timestamp=1, open=100, high=101, low=99, close=100, volume=100)]
    dec = rb.analyze(candles, ctx)
    assert dec.action == "buy"  # at least price_below triggered
PYEOF

echo "=== Storage.py method additions ==="
python3 << 'PYEOF'
with open('trade_agent/storage.py', 'r') as f:
    content = f.read()

# Add missing methods that dashboard needs
methods = '''
    def get_positions(self) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT symbol, side, quantity, entry_price, unrealized_pnl FROM positions")
        return [dict(zip(["symbol", "side", "quantity", "entry_price", "unrealized_pnl"], row)) for row in cur.fetchall()]

    def get_daily_pnl(self) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT date(timestamp) as day, sum(pnl) as pnl FROM trades GROUP BY day ORDER BY day DESC LIMIT 30")
        return [dict(zip(["day", "pnl"], row)) for row in cur.fetchall()]
'''

if 'get_positions' not in content:
    # Insert before the last method or at the end of the class
    idx = content.rfind('def ')
    if idx > 0:
        # Find the end of that function
        end_idx = content.find('\n\n', idx)
        if end_idx < 0:
            end_idx = len(content)
        content = content[:end_idx] + methods + content[end_idx:]
    with open('trade_agent/storage.py', 'w') as f:
        f.write(content)
    print("OK")
else:
    print("SKIP")
PYEOF

echo "=== Dashboard __init__.py ==="
touch trade_agent/dashboard/__init__.py
touch trade_agent/dashboard/templates/__init__.py

echo "=== Run Tests ==="
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20

echo "=== Git Commit + Push ==="
git add -A
git status --short | head -5
git commit -m "feat: Phase 3+4 — trailing stop, Kelly sizing, Bybit futures, OCO, partial exit, dashboard, rule builder, docker-compose"
git push

echo "=== DONE ==="
