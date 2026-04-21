from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class NotifyResult:
    sent: bool
    status: str


class SafeFileNotifier:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def notify(self, *, timestamp: datetime, severity: str, triggered_metrics: list[str], rates: dict[str, float], baseline_rates: dict[str, float], reason: str) -> NotifyResult:
        # Log only aggregated alert metadata by design.
        payload = {
            "timestamp": timestamp.isoformat(sep=" "),
            "severity": severity,
            "triggered_metrics": triggered_metrics,
            "rates": rates,
            "baseline_rates": baseline_rates,
            "reason": reason,
            "notification_status": "sent",
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        return NotifyResult(sent=True, status="sent")

