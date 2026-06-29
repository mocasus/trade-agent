"""SQLite storage for trades, decisions, and portfolio state."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Decision, Position, OrderResult, Balance


_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    amount_pct REAL,
    confidence INTEGER,
    reasoning TEXT,
    indicators_used TEXT,  -- JSON array
    news_factors TEXT,      -- JSON array
    metadata TEXT,          -- JSON object
    executed INTEGER DEFAULT 0,  -- 0=no, 1=yes
    executed_at REAL,
    order_id TEXT
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    price REAL NOT NULL,
    fee REAL DEFAULT 0,
    order_id TEXT,
    stop_loss REAL,
    take_profit REAL,
    pnl REAL,              -- realized PnL (NULL for open trades)
    status TEXT DEFAULT 'open'  -- open, closed, cancelled
);

CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    total_usd REAL,
    available_usd REAL,
    reserved_usd REAL,
    assets TEXT  -- JSON {symbol: amount}
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_price REAL NOT NULL,
    amount REAL NOT NULL,
    current_price REAL DEFAULT 0,
    stop_loss REAL,
    take_profit REAL,
    status TEXT DEFAULT 'open'  -- open, closed
);

CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON decisions(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
"""


class Storage:
    """SQLite-backed persistence layer."""

    def __init__(self, db_path: Path | str):
        self._path = Path(db_path).expanduser().resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def init(self) -> None:
        """Open DB and create tables if needed."""
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def shutdown(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Storage not initialized — call init() first")
        return self._conn

    # ── Decisions ──

    def log_decision(self, decision: Decision, executed: bool = False, order_id: str | None = None) -> int:
        row = (
            datetime.now().timestamp(),
            decision.symbol,
            decision.action.value,
            decision.amount_pct,
            decision.confidence,
            decision.reasoning,
            json.dumps(decision.indicators_used),
            json.dumps(decision.news_factors),
            json.dumps(decision.metadata),
            int(executed),
            datetime.now().timestamp() if executed else None,
            order_id,
        )
        cur = self.conn.execute(
            "INSERT INTO decisions (timestamp,symbol,action,amount_pct,confidence,reasoning,"
            "indicators_used,news_factors,metadata,executed,executed_at,order_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row,
        )
        self.conn.commit()
        return cur.lastrowid or 0

    def get_decisions(self, symbol: str | None = None, limit: int = 50) -> list[dict]:
        if symbol:
            rows = self.conn.execute(
                "SELECT * FROM decisions WHERE symbol=? ORDER BY timestamp DESC LIMIT ?", (symbol, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Trades ──

    def log_trade(self, result: OrderResult, stop_loss: float | None = None, take_profit: float | None = None) -> int:
        row = (
            result.timestamp,
            result.symbol,
            result.side,
            result.type,
            result.amount,
            result.price,
            result.fee,
            result.order_id,
            stop_loss,
            take_profit,
            None,  # pnl (not known yet for open trades)
            result.status,
        )
        cur = self.conn.execute(
            "INSERT INTO trades (timestamp,symbol,side,type,amount,price,fee,order_id,"
            "stop_loss,take_profit,pnl,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row,
        )
        self.conn.commit()
        return cur.lastrowid or 0

    def close_trade(self, order_id: str, pnl: float) -> None:
        self.conn.execute(
            "UPDATE trades SET pnl=?, status='closed' WHERE order_id=?", (pnl, order_id),
        )
        self.conn.commit()

    def get_trades(self, symbol: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
        q = "SELECT * FROM trades"
        params: list[Any] = []
        if symbol:
            q += " WHERE symbol=?"
            params.append(symbol)
        if status:
            q += " AND status=?"
            params.append(status)
        q += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    # ── Portfolio ──

    def save_portfolio(self, balance: Balance) -> None:
        row = (
            datetime.now().timestamp(),
            balance.total_usd,
            balance.available_usd,
            balance.reserved_usd,
            json.dumps(balance.assets),
        )
        self.conn.execute(
            "INSERT INTO portfolio (timestamp,total_usd,available_usd,reserved_usd,assets) "
            "VALUES (?,?,?,?,?)", row,
        )
        self.conn.commit()

    def get_latest_portfolio(self) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM portfolio ORDER BY timestamp DESC LIMIT 1",
        ).fetchone()
        return dict(row) if row else None

    # ── Positions ──

    def open_position(self, position: Position) -> int:
        row = (
            position.opened_at,
            position.symbol,
            position.side,
            position.entry_price,
            position.amount,
            position.current_price,
            position.stop_loss,
            position.take_profit,
            "open",
        )
        cur = self.conn.execute(
            "INSERT INTO positions (timestamp,symbol,side,entry_price,amount,"
            "current_price,stop_loss,take_profit,status) VALUES (?,?,?,?,?,?,?,?,?)", row,
        )
        self.conn.commit()
        return cur.lastrowid or 0

    def close_position(self, symbol: str, side: str) -> None:
        self.conn.execute(
            "UPDATE positions SET status='closed' WHERE symbol=? AND side=? AND status='open'",
            (symbol, side),
        )
        self.conn.commit()

    def get_open_positions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM positions WHERE status='open'",
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Stats ──

    def get_daily_pnl_pct(self) -> float:
        """Calculate today's PnL percentage from closed trades."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        row = self.conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) as total_pnl FROM trades "
            "WHERE timestamp >= ? AND status='closed'", (today_start,),
        ).fetchone()
        pnl = row["total_pnl"] if row else 0.0

        # Get starting capital from latest portfolio
        portfolio = self.get_latest_portfolio()
        if portfolio and portfolio.get("total_usd", 0) > 0:
            return pnl / portfolio["total_usd"] * 100
        return 0.0

    def get_stats(self) -> dict[str, Any]:
        """Get overall trading statistics."""
        total_trades = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE status='closed'",
        ).fetchone()["cnt"]
        winning = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE status='closed' AND pnl > 0",
        ).fetchone()["cnt"]
        total_pnl = self.conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) as total FROM trades WHERE status='closed'",
        ).fetchone()["total"]

        return {
            "total_trades": total_trades,
            "winning_trades": winning,
            "losing_trades": total_trades - winning,
            "win_rate": winning / max(total_trades, 1) * 100,
            "total_pnl": total_pnl,
        }
