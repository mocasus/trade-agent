"""Webhook notifier — sends HTTP POST."""
from __future__ import annotations

import json
from typing import Any

import httpx

from ...interfaces import NotifierInterface
from ...models import Event, Report


class WebhookNotifier(NotifierInterface):
    def __init__(self):
        self._url: str = ""
        self._method: str = "POST"
        self._headers: dict[str, str] = {}
        self._alerts: list[str] = ["all"]

    def init(self, config: dict[str, Any]) -> None:
        self._url = config.get("url", "")
        self._method = config.get("method", "POST")
        self._headers = config.get("headers", {})
        self._alerts = [a.lower() for a in config.get("alerts", ["all"])]

    def send(self, event: Event) -> bool:
        if "all" not in self._alerts and event.category not in self._alerts:
            return False
        return self._post({
            "category": event.category,
            "title": event.title,
            "message": event.message,
            "timestamp": event.timestamp,
            "data": event.data,
        })

    def send_report(self, report: Report) -> bool:
        return self._post({
            "type": "report",
            "report_type": report.report_type,
            "total_pnl": report.total_pnl,
            "total_pnl_pct": report.total_pnl_pct,
            "trades_count": report.trades_count,
            "win_rate": report.win_rate,
        })

    def _post(self, data: dict) -> bool:
        try:
            resp = httpx.request(
                self._method, self._url,
                json=data, headers=self._headers, timeout=10,
            )
            return resp.status_code < 400
        except Exception:
            return False

    def shutdown(self) -> None:
        pass


def register():
    return {"name": "webhook", "class": WebhookNotifier, "description": "HTTP webhook notifier"}
