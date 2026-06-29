"""Telegram notifier bot with command handling."""
from __future__ import annotations
import logging
import threading
from typing import Any
import httpx
from trade_agent.interfaces import NotifierInterface
from trade_agent.models import Event, Report

logger = logging.getLogger("trade-agent.notifier.telegram")


class TelegramNotifier(NotifierInterface):
    def __init__(self):
        self._token: str = ""
        self._chat_id: str = ""
        self._base_url: str = ""
        self._alerts: list[str] = []
        self._commands_enabled: bool = True
        self._poll_thread: threading.Thread | None = None
        self._running: bool = False
        self._command_handler = None
        self._offset: int = 0

    def init(self, config: dict[str, Any]) -> None:
        self._token = config.get("bot_token", "")
        self._chat_id = str(config.get("chat_id", ""))
        self._base_url = f"https://api.telegram.org/bot{self._token}"
        self._alerts = [a.lower() for a in config.get("alerts", ["trade", "stop_loss", "error", "kill_switch"])]
        self._commands_enabled = config.get("commands", True)

    def set_command_handler(self, handler) -> None:
        self._command_handler = handler

    def send(self, event: Event) -> bool:
        if event.category not in self._alerts:
            return False
        text = f"*{event.title}*\n{event.message}"
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

    def start_polling(self) -> None:
        if not self._commands_enabled or not self._token:
            return
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        import time
        while self._running:
            try:
                resp = httpx.get(
                    f"{self._base_url}/getUpdates",
                    params={"offset": self._offset, "timeout": 30},
                    timeout=35,
                )
                if resp.status_code != 200:
                    time.sleep(5)
                    continue
                data = resp.json()
                for update in data.get("result", []):
                    self._offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "")
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    if chat_id != self._chat_id:
                        continue
                    if text.startswith("/") and self._command_handler:
                        parts = text[1:].split()
                        cmd = parts[0] if parts else ""
                        args = parts[1:]
                        response = self._command_handler(cmd, args)
                        if response:
                            self._send_message(response)
            except Exception:
                time.sleep(5)

    def handle_command(self, command: str, args: list[str]) -> str | None:
        commands = {
            "start": "Trade Agent running. Commands: /status /portfolio /stop",
            "status": "Agent running normally.",
            "help": "Commands: /start /status /portfolio /stop",
        }
        return commands.get(command)

    def shutdown(self) -> None:
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)


def register():
    return {"name": "telegram", "class": TelegramNotifier, "description": "Telegram bot notifier with commands"}
