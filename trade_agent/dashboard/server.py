"""Minimal read-only HTTP dashboard."""

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
        return {
            "total_trades": len(trades),
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "status": "running",
        }

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
