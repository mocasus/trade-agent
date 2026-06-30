"""Console notifier — prints to stdout."""

from __future__ import annotations

from typing import Any

from trade_agent.interfaces import NotifierInterface
from trade_agent.models import Event, Report


class ConsoleNotifier(NotifierInterface):
    def __init__(self):
        self._alerts: list[str] = ["all"]

    def init(self, config: dict[str, Any]) -> None:
        alerts = config.get("alerts", ["all"])
        self._alerts = [a.lower() for a in alerts]

    def send(self, event: Event) -> bool:
        if "all" in self._alerts or event.category in self._alerts:
            print(f"\n🔔 [{event.category}] {event.title}\n   {event.message}\n")
            return True
        return False

    def send_report(self, report: Report) -> bool:
        print(f"\n📊 {report.report_type.upper()} REPORT")
        print(f"   P&L: ${report.total_pnl:.2f} ({report.total_pnl_pct:.1f}%)")
        print(f"   Trades: {report.trades_count} | Win rate: {report.win_rate:.1f}%")
        print(f"   Open positions: {len(report.open_positions)}\n")
        return True

    def shutdown(self) -> None:
        pass


def register():
    return {
        "name": "console",
        "class": ConsoleNotifier,
        "description": "Console stdout notifier",
    }
