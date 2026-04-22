from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.auth_codes import format_top_auth_codes


Severity = Literal["none", "info", "warning", "critical"]
Recommendation = Literal["alert", "no_alert"]
MetricName = Literal["denied", "failed", "reversed"]
DecisionOverallStatus = Literal["normal", "watch", "act_now"]
DecisionEngineMode = Literal["local", "external"]
ExternalAIProvider = Literal["openai", "anthropic", "google"]


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
    auth_code_top: list[tuple[str, int]] = Field(default_factory=list)
    auth_code_top_display: str = ""

    @model_validator(mode="after")
    def populate_auth_code_top_display(self) -> "AlertRecord":
        if not self.auth_code_top_display:
            self.auth_code_top_display = format_top_auth_codes(self.auth_code_top)
        return self


class AlertsResponse(BaseModel):
    alerts: list[AlertRecord]


class DecisionPriorityItem(BaseModel):
    metric: MetricName
    decision_status: DecisionOverallStatus
    current_severity: Severity
    forecast_severity: Severity | None = None
    risk_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    current_rate: float = Field(ge=0.0, le=1.0)
    baseline_rate: float = Field(ge=0.0, le=1.0)
    forecast_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    recommended_action: str
    root_cause_hint: str
    top_auth_codes: list[tuple[str, int]] = Field(default_factory=list)
    top_auth_codes_display: str = ""

    @model_validator(mode="after")
    def populate_top_auth_codes_display(self) -> "DecisionPriorityItem":
        if not self.top_auth_codes_display:
            self.top_auth_codes_display = format_top_auth_codes(self.top_auth_codes)
        return self


class DecisionForecastPoint(BaseModel):
    timestamp: datetime
    metric: MetricName
    forecast_rate: float = Field(ge=0.0, le=1.0)


class DecisionEvidence(BaseModel):
    timestamp: datetime
    source: Literal["metrics", "alerts", "decision"]
    message: str
    auth_code_top: list[tuple[str, int]] = Field(default_factory=list)
    auth_code_top_display: str = ""

    @model_validator(mode="after")
    def populate_auth_code_top_display(self) -> "DecisionEvidence":
        if not self.auth_code_top_display:
            self.auth_code_top_display = format_top_auth_codes(self.auth_code_top)
        return self


class DecisionProviderStatus(BaseModel):
    mode: DecisionEngineMode
    provider: ExternalAIProvider | None = None
    model: str | None = None
    fallback_active: bool
    last_error: str | None = None


class DecisionResponse(BaseModel):
    generated_at: datetime
    overall_status: DecisionOverallStatus
    top_recommendation: str
    summary: str
    priority_items: list[DecisionPriorityItem]
    forecast_points: list[DecisionForecastPoint]
    recent_evidence: list[DecisionEvidence]
    provider_status: DecisionProviderStatus
