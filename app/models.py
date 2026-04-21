from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Severity = Literal["none", "info", "warning", "critical"]
Recommendation = Literal["alert", "no_alert"]
MetricName = Literal["denied", "failed", "reversed"]


class MonitorRequest(BaseModel):
    window_end: datetime
    approved: int = Field(ge=0, le=1_000_000)
    denied: int = Field(ge=0, le=1_000_000)
    failed: int = Field(ge=0, le=1_000_000)
    reversed: int = Field(ge=0, le=1_000_000)
    backend_reversed: int = Field(ge=0, le=1_000_000)
    refunded: int = Field(ge=0, le=1_000_000)
    auth_code_counts: dict[str, int] | None = None

    @field_validator("auth_code_counts")
    @classmethod
    def validate_auth_code_counts(cls, value: dict[str, int] | None) -> dict[str, int] | None:
        if value is None:
            return None
        if len(value) > 32:
            raise ValueError("auth_code_counts cannot have more than 32 keys")
        for key, count in value.items():
            if len(key) > 16:
                raise ValueError("auth_code key length cannot exceed 16")
            if count < 0 or count > 1_000_000:
                raise ValueError("auth_code count must be between 0 and 1_000_000")
        return value


class Rates(BaseModel):
    denied_rate: float
    failed_rate: float
    reversed_rate: float


class MonitorResponse(BaseModel):
    window_end: datetime
    recommendation: Recommendation
    severity: Severity
    triggered_metrics: list[MetricName]
    rates: Rates
    baseline_rates: Rates
    notification_sent: bool
    reason: str


class MetricsRow(BaseModel):
    timestamp: datetime
    total: int
    approved_rate: float
    denied_rate: float
    failed_rate: float
    reversed_rate: float
    alert_severity: Severity


class MetricsResponse(BaseModel):
    rows: list[MetricsRow]


class AlertRecord(BaseModel):
    timestamp: datetime
    severity: Severity
    triggered_metrics: list[MetricName]
    rates: Rates
    baseline_rates: Rates
    notification_status: Literal["sent", "suppressed", "skipped"]
    reason: str
    auth_code_top: list[tuple[str, int]] = []


class AlertsResponse(BaseModel):
    alerts: list[AlertRecord]

