"""
Product 07 — Production Service & Reliability
Live Telemetry & Alert Manager.
Dispatches operational notifications and trade signals to Telegram, Discord, and system logs.
"""

import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional


class AlertManager:
    """
    Unified telemetry dispatcher for production operations.
    """

    def __init__(
        self,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        enable_console: bool = True
    ):
        self.telegram_bot_token = telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.enable_console = enable_console

    def send_alert(
        self,
        level: str,
        title: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Sends formatted alert to configured channels.
        """
        icon = "🟢" if level == "INFO" else ("🟡" if level == "WARNING" else "🔴")
        formatted = f"{icon} [{level.upper()}] {title}\n{message}"
        if payload:
            formatted += f"\n```json\n{json.dumps(payload, indent=2)}\n```"

        if self.enable_console:
            print(f"\n📢 [ALERT_MANAGER]: {formatted}\n")

        if self.telegram_bot_token and self.telegram_chat_id:
            self._dispatch_telegram(formatted)

    def _dispatch_telegram(self, text: str) -> None:
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": self.telegram_chat_id, "text": text}).encode("utf-8")
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass
        except Exception as e:
            if self.enable_console:
                print(f"⚠️ [ALERT_MANAGER]: Telegram dispatch failed: {e}")
