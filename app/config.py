from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str
    port: int
    monitoring_api_key: str | None
    max_monitor_request_bytes: int
    max_count_value: int
    max_auth_code_keys: int
    max_auth_code_key_length: int
    minimum_total_count: int
    minimum_metric_count: int
    baseline_window_minutes: int
    cooldown_minutes: int
    floor_rate_denied: float
    floor_rate_failed: float
    floor_rate_reversed: float
    warning_multiplier: float
    critical_multiplier: float


def load_settings() -> Settings:
    root = Path(__file__).resolve().parents[1]
    return Settings(
        data_dir=Path(os.getenv("DATA_DIR", root / "database")),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        monitoring_api_key=os.getenv("MONITORING_API_KEY"),
        max_monitor_request_bytes=int(os.getenv("MAX_MONITOR_REQUEST_BYTES", "65536")),
        max_count_value=int(os.getenv("MAX_COUNT_VALUE", "1000000")),
        max_auth_code_keys=int(os.getenv("MAX_AUTH_CODE_KEYS", "32")),
        max_auth_code_key_length=int(os.getenv("MAX_AUTH_CODE_KEY_LENGTH", "16")),
        minimum_total_count=int(os.getenv("MINIMUM_TOTAL_COUNT", "80")),
        minimum_metric_count=int(os.getenv("MINIMUM_METRIC_COUNT", "3")),
        baseline_window_minutes=int(os.getenv("BASELINE_WINDOW_MINUTES", "60")),
        cooldown_minutes=int(os.getenv("COOLDOWN_MINUTES", "10")),
        floor_rate_denied=float(os.getenv("FLOOR_RATE_DENIED", "0.08")),
        floor_rate_failed=float(os.getenv("FLOOR_RATE_FAILED", "0.02")),
        floor_rate_reversed=float(os.getenv("FLOOR_RATE_REVERSED", "0.03")),
        warning_multiplier=float(os.getenv("WARNING_MULTIPLIER", "2.0")),
        critical_multiplier=float(os.getenv("CRITICAL_MULTIPLIER", "3.0")),
    )
