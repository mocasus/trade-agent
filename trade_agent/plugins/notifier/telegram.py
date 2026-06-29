"""Telegram notifier bot."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ...interfaces import NotifierInterface
from ...models import Event, Report

logger = logging.getLogger("trade-agent.notifier.telegram")


class TelegramNotifier(NotifierInterface):
    def __init__(self):
        self._token: str = ""
        self._chat_id: str = ""
        self._alerts: list[str] = []
        self._base_url: str = ""

    def init(self, config: dict[str, Any]) -> None:
        self._token = config.get("bot_token", "")
        self._chat_id = config.get("chat_id", "")
        self._base_url = f"https://api.telegram.org/bot{self._token}"
        self._alerts = [a.lower() for a in config.get("alerts", ["trade", "stop_loss", "error", "kill_switch"])]

    def send(self, event: Event) -> bool:
        if event.category not in self._alerts:
            return False

        text = f"*{event.title}*\n{event.message}"
        if event.data:
            for k, v in event.data.items():
                text += f"\n{k}: {v}"

        return self._send_message(text)

    def send_report(self, report: Report) -> bool:
        text = (
            f"*{report.report_type.upper()} REPORT*\n"
            f"P&L: ${report.total_pnl:.2f} ({report.total_pnl_pct:.1f}%)\n"
            f"Trades: {report.trades_count} | Win: {report.win_rate:.1f}%\n"
            f"Open: {len(report.open_positions)}"
        )
        return self._send_message(text)

    def _send_message(self, text: str) -> bool:
        try:
            resp = httpx.post(
                f"{self._base_url}/sendMessage",
                json={"chat_id": self._chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False

    def shutdown(self) -> None:
        pass


def register():
    return {"name": "telegram", "class": TelegramNotifier, "description": "Telegram bot notifier"}
