from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class HistoricalRow:
    timestamp: datetime
    counts: dict[str, int]
    auth_code_counts: dict[str, int]


def _status_defaults() -> dict[str, int]:
    return {
        "approved": 0,
        "denied": 0,
        "failed": 0,
        "reversed": 0,
        "backend_reversed": 0,
        "refunded": 0,
    }


def load_transactions(data_dir: Path) -> list[HistoricalRow]:
    tx_path = data_dir / "transactions.csv"
    auth_path = data_dir / "transactions_auth_codes.csv"

    status_map: dict[datetime, dict[str, int]] = defaultdict(_status_defaults)
    with tx_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ts = datetime.fromisoformat(row["timestamp"])
            status_map[ts][row["status"]] = int(row["count"])

    auth_map: dict[datetime, dict[str, int]] = defaultdict(dict)
    with auth_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ts = datetime.fromisoformat(row["timestamp"])
            auth_map[ts][row["auth_code"]] = int(row["count"])

    rows: list[HistoricalRow] = []
    for ts in sorted(status_map):
        rows.append(
            HistoricalRow(
                timestamp=ts,
                counts=status_map[ts],
                auth_code_counts=auth_map.get(ts, {}),
            )
        )
    return rows


def compute_rates(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if total <= 0:
        return {
            "approved_rate": 0.0,
            "denied_rate": 0.0,
            "failed_rate": 0.0,
            "reversed_rate": 0.0,
        }
    return {
        "approved_rate": counts.get("approved", 0) / total,
        "denied_rate": counts.get("denied", 0) / total,
        "failed_rate": counts.get("failed", 0) / total,
        "reversed_rate": counts.get("reversed", 0) / total,
    }

