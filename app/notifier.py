from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx


@dataclass(frozen=True)
class NotifyResult:
    sent: bool
    status: str
    team_notification_status: str
    notification_channels: list[str]


class AlertNotifier:
    def __init__(self, log_path: Path, webhook_url: str | None = None, webhook_timeout_seconds: float = 5.0) -> None:
        self.log_path = log_path
        self.webhook_url = webhook_url
        self.webhook_timeout_seconds = webhook_timeout_seconds
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_log(self, payload: dict[str, object]) -> None:
        payload = {
            **payload,
            "notification_status": "sent",
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _send_webhook(self, payload: dict[str, object]) -> str:
        if not self.webhook_url:
            return "disabled"
        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=self.webhook_timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError:
            return "failed"
        return "sent"

    def notify(
        self,
        *,
        timestamp: datetime,
        severity: str,
        triggered_metrics: list[str],
        rates: dict[str, float],
        baseline_rates: dict[str, float],
        reason: str,
        auth_code_top: list[tuple[str, int]],
    ) -> NotifyResult:
        # Log and notify using aggregate-only metadata.
        payload = {
            "timestamp": timestamp.isoformat(sep=" "),
            "severity": severity,
            "triggered_metrics": triggered_metrics,
            "rates": rates,
            "baseline_rates": baseline_rates,
            "reason": reason,
            "auth_code_top": auth_code_top,
        }
        self._write_log(payload)
        team_status = self._send_webhook(payload)
        channels = ["log"]
        if self.webhook_url:
            channels.append("webhook")
        return NotifyResult(
            sent=True,
            status="sent",
            team_notification_status=team_status,
            notification_channels=channels,
        )
