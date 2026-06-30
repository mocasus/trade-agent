"""Discord webhook notifier plugin."""

from __future__ import annotations
import logging
from typing import Any
import httpx
from trade_agent.interfaces import NotifierInterface
from trade_agent.models import Event, Report

logger = logging.getLogger("trade-agent.notifier.discord")


class DiscordNotifier(NotifierInterface):
    def __init__(self):
        self._url: str = ""
        self._alerts: list[str] = []

    def init(self, config: dict[str, Any]) -> None:
        self._url = config.get("webhook_url", "")
        self._alerts = [
            a.lower() for a in config.get("alerts", ["trade", "stop_loss", "error"])
        ]

    def send(self, event: Event) -> bool:
        if event.category not in self._alerts:
            return False
        color = (
            0x00FF00
            if "trade" in event.category
            else 0xFF0000
            if "error" in event.category
            else 0x0099FF
        )
        payload = {
            "embeds": [
                {"title": event.title, "description": event.message, "color": color}
            ]
        }
        try:
            resp = httpx.post(self._url, json=payload, timeout=10)
            return resp.status_code < 400
        except Exception as e:
            logger.error("Discord send failed: %s", e)
            return False

    def send_report(self, report: Report) -> bool:
        payload = {
            "embeds": [
                {
                    "title": f"{report.report_type.upper()} REPORT",
                    "fields": [
                        {
                            "name": "P&L",
                            "value": f"${report.total_pnl:.2f} ({report.total_pnl_pct:.1f}%)",
                            "inline": True,
                        },
                        {
                            "name": "Trades",
                            "value": str(report.trades_count),
                            "inline": True,
                        },
                        {
                            "name": "Win Rate",
                            "value": f"{report.win_rate:.1f}%",
                            "inline": True,
                        },
                    ],
                    "color": 0x0099FF,
                }
            ]
        }
        try:
            resp = httpx.post(self._url, json=payload, timeout=10)
            return resp.status_code < 400
        except Exception:
            return False

    def shutdown(self) -> None:
        pass


def register():
    return {
        "name": "discord",
        "class": DiscordNotifier,
        "description": "Discord webhook notifier",
    }
