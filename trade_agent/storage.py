     1|"""SQLite storage for trades, decisions, and portfolio state."""
     2|from __future__ import annotations
     3|
     4|import json
     5|import sqlite3
     6|from datetime import datetime
     7|from pathlib import Path
     8|from typing import Any
     9|
    10|from .models import Decision, Position, OrderResult, Balance
    11|
    12|
    13|_SCHEMA = """
    14|CREATE TABLE IF NOT EXISTS decisions (
    15|    id INTEGER PRIMARY KEY AUTOINCREMENT,
    16|    timestamp REAL NOT NULL,
    17|    symbol TEXT NOT NULL,
    18|    action TEXT NOT NULL,
    19|    amount_pct REAL,
    20|    confidence INTEGER,
    21|    reasoning TEXT,
    22|    indicators_used TEXT,  -- JSON array
    23|    news_factors TEXT,      -- JSON array
    24|    metadata TEXT,          -- JSON object
    25|    executed INTEGER DEFAULT 0,  -- 0=no, 1=yes
    26|    executed_at REAL,
    27|    order_id TEXT
    28|);
    29|
    30|CREATE TABLE IF NOT EXISTS trades (
    31|    id INTEGER PRIMARY KEY AUTOINCREMENT,
    32|    timestamp REAL NOT NULL,
    33|    symbol TEXT NOT NULL,
    34|    side TEXT NOT NULL,
    35|    type TEXT NOT NULL,
    36|    amount REAL NOT NULL,
    37|    price REAL NOT NULL,
    38|    fee REAL DEFAULT 0,
    39|    order_id TEXT,
    40|    stop_loss REAL,
    41|    take_profit REAL,
    42|    pnl REAL,              -- realized PnL (NULL for open trades)
    43|    status TEXT DEFAULT 'open'  -- open, closed, cancelled
    44|);
    45|
    46|CREATE TABLE IF NOT EXISTS portfolio (
    47|    id INTEGER PRIMARY KEY AUTOINCREMENT,
    48|    timestamp REAL NOT NULL,
    49|    total_usd REAL,
    50|    available_usd REAL,
    51|    reserved_usd REAL,
    52|    assets TEXT  -- JSON {symbol: amount}
    53|);
    54|
    55|CREATE TABLE IF NOT EXISTS positions (
    56|    id INTEGER PRIMARY KEY AUTOINCREMENT,
    57|    timestamp REAL NOT NULL,
    58|    symbol TEXT NOT NULL,
    59|    side TEXT NOT NULL,
    60|    entry_price REAL NOT NULL,
    61|    amount REAL NOT NULL,
    62|    current_price REAL DEFAULT 0,
    63|    stop_loss REAL,
    64|    take_profit REAL,
    65|    status TEXT DEFAULT 'open'  -- open, closed
    66|);
    67|
    68|CREATE INDEX IF NOT EXISTS idx_decisions_symbol ON decisions(symbol);
    69|CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
    70|CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
    71|"""
    72|
    73|
    74|class Storage:
    75|    """SQLite-backed persistence layer."""
    76|
    77|    def __init__(self, db_path: Path | str):
    78|        self._path = Path(db_path).expanduser().resolve()
    79|        self._path.parent.mkdir(parents=True, exist_ok=True)
    80|        self._conn: sqlite3.Connection | None = None
    81|
    82|    def init(self) -> None:
    83|        """Open DB and create tables if needed."""
    84|        self._conn = sqlite3.connect(str(self._path))
    85|        self._conn.row_factory = sqlite3.Row
    86|        self.conn.executescript(_SCHEMA)
    87|        self.conn.commit()
    88|
    89|    def shutdown(self) -> None:
    90|        if self._conn:
    91|            self._conn.close()
    92|            self._conn = None
    93|
    94|    @property
    95|    def conn(self) -> sqlite3.Connection:
    96|        if self._conn is None:
    97|            raise RuntimeError("Storage not initialized — call init() first")
    98|        return self._conn
    99|
   100|    # ── Decisions ──
   101|
   102|    def log_decision(self, decision: Decision, executed: bool = False, order_id: str | None = None) -> int:
   103|        row = (
   104|            datetime.now().timestamp(),
   105|            decision.symbol,
   106|            decision.action.value,
   107|            decision.amount_pct,
   108|            decision.confidence,
   109|            decision.reasoning,
   110|            json.dumps(decision.indicators_used),
   111|            json.dumps(decision.news_factors),
   112|            json.dumps(decision.metadata),
   113|            int(executed),
   114|            datetime.now().timestamp() if executed else None,
   115|            order_id,
   116|        )
   117|        cur = self.conn.execute(
   118|            "INSERT INTO decisions (timestamp,symbol,action,amount_pct,confidence,reasoning,"
   119|            "indicators_used,news_factors,metadata,executed,executed_at,order_id) "
   120|            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row,
   121|        )
   122|        self.conn.commit()
   123|        return cur.lastrowid or 0
   124|
   125|    def get_decisions(self, symbol: str | None = None, limit: int = 50) -> list[dict]:
   126|        if symbol:
   127|            rows = self.conn.execute(
   128|                "SELECT * FROM decisions WHERE symbol=? ORDER BY timestamp DESC LIMIT ?", (symbol, limit),
   129|            ).fetchall()
   130|        else:
   131|            rows = self.conn.execute(
   132|                "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,),
   133|            ).fetchall()
   134|        return [dict(r) for r in rows]
   135|
   136|    # ── Trades ──
   137|
   138|    def log_trade(self, result: OrderResult, stop_loss: float | None = None, take_profit: float | None = None) -> int:
   139|        row = (
   140|            result.timestamp,
   141|            result.symbol,
   142|            result.side,
   143|            result.type,
   144|            result.amount,
   145|            result.price,
   146|            result.fee,
   147|            result.order_id,
   148|            stop_loss,
   149|            take_profit,
   150|            None,  # pnl (not known yet for open trades)
   151|            result.status,
   152|        )
   153|        cur = self.conn.execute(
   154|            "INSERT INTO trades (timestamp,symbol,side,type,amount,price,fee,order_id,"
   155|            "stop_loss,take_profit,pnl,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row,
   156|        )
   157|        self.conn.commit()
   158|        return cur.lastrowid or 0
   159|
   160|    def close_trade(self, order_id: str, pnl: float) -> None:
   161|        self.conn.execute(
   162|            "UPDATE trades SET pnl=?, status='closed' WHERE order_id=?", (pnl, order_id),
   163|        )
   164|        self.conn.commit()
   165|
   166|    def get_trades(self, symbol: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
   167|        q = "SELECT * FROM trades"
   168|        params: list[Any] = []
   169|        if symbol:
   170|            q += " WHERE symbol=?"
   171|            params.append(symbol)
   172|        if status:
   173|            q += " AND status=?"
   174|            params.append(status)
   175|        q += " ORDER BY timestamp DESC LIMIT ?"
   176|        params.append(limit)
   177|        rows = self.conn.execute(q, params).fetchall()
   178|        return [dict(r) for r in rows]
   179|
   180|    # ── Portfolio ──
   181|
   182|    def save_portfolio(self, balance: Balance) -> None:
   183|        row = (
   184|            datetime.now().timestamp(),
   185|            balance.total_usd,
   186|            balance.available_usd,
   187|            balance.reserved_usd,
   188|            json.dumps(balance.assets),
   189|        )
   190|        self.conn.execute(
   191|            "INSERT INTO portfolio (timestamp,total_usd,available_usd,reserved_usd,assets) "
   192|            "VALUES (?,?,?,?,?)", row,
   193|        )
   194|        self.conn.commit()
   195|
   196|    def get_latest_portfolio(self) -> dict | None:
   197|        row = self.conn.execute(
   198|            "SELECT * FROM portfolio ORDER BY timestamp DESC LIMIT 1",
   199|        ).fetchone()
   200|        return dict(row) if row else None
   201|
   202|    # ── Positions ──
   203|
   204|    def open_position(self, position: Position) -> int:
   205|        row = (
   206|            position.opened_at,
   207|            position.symbol,
   208|            position.side,
   209|            position.entry_price,
   210|            position.amount,
   211|            position.current_price,
   212|            position.stop_loss,
   213|            position.take_profit,
   214|            "open",
   215|        )
   216|        cur = self.conn.execute(
   217|            "INSERT INTO positions (timestamp,symbol,side,entry_price,amount,"
   218|            "current_price,stop_loss,take_profit,status) VALUES (?,?,?,?,?,?,?,?,?)", row,
   219|        )
   220|        self.conn.commit()
   221|        return cur.lastrowid or 0
   222|
   223|    def close_position(self, symbol: str, side: str) -> None:
   224|        self.conn.execute(
   225|            "UPDATE positions SET status='closed' WHERE symbol=? AND side=? AND status='open'",
   226|            (symbol, side),
   227|        )
   228|        self.conn.commit()
   229|
   230|    def get_open_positions(self) -> list[dict]:
   231|        rows = self.conn.execute(
   232|            "SELECT * FROM positions WHERE status='open'",
   233|        ).fetchall()
   234|        return [dict(r) for r in rows]
   235|
   236|    # ── Stats ──
   237|
   238|    def get_daily_pnl_pct(self) -> float:
   239|        """Calculate today's PnL percentage from closed trades."""
   240|        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
   241|        row = self.conn.execute(
   242|            "SELECT COALESCE(SUM(pnl), 0) as total_pnl FROM trades "
   243|            "WHERE timestamp >= ? AND status='closed'", (today_start,),
   244|        ).fetchone()
   245|        pnl = row["total_pnl"] if row else 0.0
   246|
   247|        # Get starting capital from latest portfolio
   248|        portfolio = self.get_latest_portfolio()
   249|        if portfolio and portfolio.get("total_usd", 0) > 0:
   250|            return pnl / portfolio["total_usd"] * 100
   251|        return 0.0
   252|
   253|    def get_stats(self) -> dict[str, Any]:
   254|        """Get overall trading statistics."""
   255|        total_trades = self.conn.execute(
   256|            "SELECT COUNT(*) as cnt FROM trades WHERE status='closed'",
   257|        ).fetchone()["cnt"]
   258|        winning = self.conn.execute(
   259|            "SELECT COUNT(*) as cnt FROM trades WHERE status='closed' AND pnl > 0",
   260|        ).fetchone()["cnt"]
   261|        total_pnl = self.conn.execute(
   262|            "SELECT COALESCE(SUM(pnl), 0) as total FROM trades WHERE status='closed'",
   263|        ).fetchone()["total"]
   264|
   265|        return {
   266|            "total_trades": total_trades,
   267|            "winning_trades": winning,
   268|            "losing_trades": total_trades - winning,
   269|            "win_rate": winning / max(total_trades, 1) * 100,
   270|            "total_pnl": total_pnl,
   271|        }
   272|