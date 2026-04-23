from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


DecisionEngineMode = Literal["local", "external"]
ExternalAIProvider = Literal["openai", "anthropic", "google"]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    host: str
    port: int
    monitoring_api_key: str | None
    team_notification_webhook_url: str | None
    team_notification_timeout_seconds: float
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
    decision_engine_mode: DecisionEngineMode
    decision_lookback_minutes: int
    decision_forecast_horizon_minutes: int
    decision_forecast_step_minutes: int
    decision_min_history_points: int
    external_ai_provider: ExternalAIProvider | None
    external_ai_model: str | None
    external_ai_api_key: str | None
    external_ai_base_url: str | None
    external_ai_timeout_seconds: float


def load_settings() -> Settings:
    root = Path(__file__).resolve().parents[1]
    decision_engine_mode = os.getenv("DECISION_ENGINE_MODE", "local").strip().lower()
    if decision_engine_mode not in {"local", "external"}:
        decision_engine_mode = "local"

    external_ai_provider = os.getenv("EXTERNAL_AI_PROVIDER")
    if external_ai_provider:
        external_ai_provider = external_ai_provider.strip().lower()
    if external_ai_provider not in {"openai", "anthropic", "google"}:
        external_ai_provider = None

    return Settings(
        data_dir=Path(os.getenv("DATA_DIR", root / "database")),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        monitoring_api_key=os.getenv("MONITORING_API_KEY"),
        team_notification_webhook_url=(os.getenv("TEAM_NOTIFICATION_WEBHOOK_URL") or "").strip() or None,
        team_notification_timeout_seconds=float(os.getenv("TEAM_NOTIFICATION_TIMEOUT_SECONDS", "5")),
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
        decision_engine_mode=decision_engine_mode,
        decision_lookback_minutes=int(os.getenv("DECISION_LOOKBACK_MINUTES", "15")),
        decision_forecast_horizon_minutes=int(os.getenv("DECISION_FORECAST_HORIZON_MINUTES", "30")),
        decision_forecast_step_minutes=int(os.getenv("DECISION_FORECAST_STEP_MINUTES", "5")),
        decision_min_history_points=int(os.getenv("DECISION_MIN_HISTORY_POINTS", "1")),
        external_ai_provider=external_ai_provider,
        external_ai_model=os.getenv("EXTERNAL_AI_MODEL"),
        external_ai_api_key=os.getenv("EXTERNAL_AI_API_KEY"),
        external_ai_base_url=(os.getenv("EXTERNAL_AI_BASE_URL") or "").strip() or None,
        external_ai_timeout_seconds=float(os.getenv("EXTERNAL_AI_TIMEOUT_SECONDS", "10")),
    )
