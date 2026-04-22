from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException

from app.anomaly import AlertEngine
from app.config import Settings, load_settings
from app.data_loader import HistoricalRow, compute_rates, load_transactions
from app.decision import DecisionEngine
from app.models import AlertRecord, AlertsResponse, DecisionResponse, MetricsResponse, MetricsRow, MonitorRequest, MonitorResponse, Rates
from app.notifier import SafeFileNotifier
from app.security import MonitorPayloadLimitMiddleware, build_api_key_guard


@dataclass
class RuntimeState:
    rows: list[HistoricalRow]
    engine: AlertEngine
    decision_engine: DecisionEngine
    notifier: SafeFileNotifier
    auth_codes_by_timestamp: dict[datetime, dict[str, int]] = field(default_factory=dict)
    alert_history: list[AlertRecord] = field(default_factory=list)


def _build_metrics_rows(rows: list[HistoricalRow], engine: AlertEngine) -> list[MetricsRow]:
    metrics_rows: list[MetricsRow] = []
    for row in rows:
        eval_result = engine.evaluate(timestamp=row.timestamp, counts=row.counts, apply_cooldown=False)
        rates = compute_rates(row.counts)
        metrics_rows.append(
            MetricsRow(
                timestamp=row.timestamp,
                total=sum(row.counts.values()),
                approved_rate=round(rates["approved_rate"], 6),
                denied_rate=round(rates["denied_rate"], 6),
                failed_rate=round(rates["failed_rate"], 6),
                reversed_rate=round(rates["reversed_rate"], 6),
                alert_severity=eval_result.severity,
            )
        )
    return metrics_rows


def _upsert_metrics_row(rows: list[MetricsRow], row: MetricsRow) -> list[MetricsRow]:
    updated = []
    inserted = False
    for existing in rows:
        if existing.timestamp == row.timestamp:
            updated.append(row)
            inserted = True
        else:
            updated.append(existing)
    if not inserted:
        updated.append(row)
    updated.sort(key=lambda item: item.timestamp)
    return updated


def _normalize_timestamp(timestamp: datetime) -> datetime:
    return timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp


def _upsert_historical_row(rows: list[HistoricalRow], row: HistoricalRow) -> list[HistoricalRow]:
    updated = []
    inserted = False
    for existing in rows:
        if existing.timestamp == row.timestamp:
            updated.append(row)
            inserted = True
        else:
            updated.append(existing)
    if not inserted:
        updated.append(row)
    updated.sort(key=lambda item: item.timestamp)
    return updated


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    rows = load_transactions(cfg.data_dir)
    notifier = SafeFileNotifier(Path("logs/alerts.log"))
    engine = AlertEngine(settings=cfg, historical_rows=rows)
    decision_engine = DecisionEngine(settings=cfg, alert_engine=engine)
    state = RuntimeState(rows=rows, engine=engine, decision_engine=decision_engine, notifier=notifier)
    state.auth_codes_by_timestamp = {row.timestamp: row.auth_code_counts for row in rows}
    api_key_guard = build_api_key_guard(cfg.monitoring_api_key)

    app = FastAPI(title="CloudWalk Monitoring Test Submission", version="0.1.0")
    app.add_middleware(MonitorPayloadLimitMiddleware, max_bytes=cfg.max_monitor_request_bytes)
    app.state.runtime = state
    app.state.settings = cfg
    app.state.metrics_rows = _build_metrics_rows(rows, engine)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/monitor", response_model=MonitorResponse, dependencies=[Depends(api_key_guard)])
    async def monitor(payload: MonitorRequest) -> MonitorResponse:
        normalized_window_end = _normalize_timestamp(payload.window_end)
        counts = {
            "approved": payload.approved,
            "denied": payload.denied,
            "failed": payload.failed,
            "reversed": payload.reversed,
            "backend_reversed": payload.backend_reversed,
            "refunded": payload.refunded,
        }
        # Hard limits from security requirements.
        for key, value in counts.items():
            if value > cfg.max_count_value:
                raise HTTPException(status_code=422, detail=f"{key} exceeds max_count_value")
        if payload.auth_code_counts and len(payload.auth_code_counts) > cfg.max_auth_code_keys:
            raise HTTPException(status_code=422, detail="auth_code_counts exceeds key limit")

        eval_result = state.engine.evaluate(normalized_window_end, counts, apply_cooldown=True)
        sent = False
        status_text = "skipped"
        historical_auth_codes = payload.auth_code_counts or state.auth_codes_by_timestamp.get(normalized_window_end, {})
        state.auth_codes_by_timestamp[normalized_window_end] = historical_auth_codes
        if eval_result.recommendation == "alert":
            notify_result = state.notifier.notify(
                timestamp=normalized_window_end,
                severity=eval_result.severity,
                triggered_metrics=eval_result.triggered_metrics,
                rates=eval_result.rates,
                baseline_rates=eval_result.baseline_rates,
                reason=eval_result.reason,
            )
            sent = notify_result.sent
            status_text = notify_result.status

            auth_top = sorted(historical_auth_codes.items(), key=lambda kv: kv[1], reverse=True)[:5]
            state.alert_history.append(
                AlertRecord(
                    timestamp=normalized_window_end,
                    severity=eval_result.severity,
                    triggered_metrics=eval_result.triggered_metrics,
                    rates=Rates(**eval_result.rates),
                    baseline_rates=Rates(**eval_result.baseline_rates),
                    notification_status=status_text,
                    reason=eval_result.reason,
                    auth_code_top=auth_top,
                )
            )

        updated_rows = _upsert_historical_row(
            state.rows,
            HistoricalRow(
                timestamp=normalized_window_end,
                counts=counts.copy(),
                auth_code_counts=historical_auth_codes,
            ),
        )
        state.rows = updated_rows
        state.engine.historical_rows = updated_rows
        state.engine.global_baseline = state.engine._compute_global_baseline()

        app.state.metrics_rows = _upsert_metrics_row(
            app.state.metrics_rows,
            MetricsRow(
                timestamp=normalized_window_end,
                total=sum(counts.values()),
                approved_rate=round(counts["approved"] / max(1, sum(counts.values())), 6),
                denied_rate=round(eval_result.rates["denied_rate"], 6),
                failed_rate=round(eval_result.rates["failed_rate"], 6),
                reversed_rate=round(eval_result.rates["reversed_rate"], 6),
                alert_severity=eval_result.severity,
            ),
        )

        return MonitorResponse(
            window_end=normalized_window_end,
            recommendation=eval_result.recommendation,
            severity=eval_result.severity,
            triggered_metrics=eval_result.triggered_metrics,
            rates=Rates(**eval_result.rates),
            baseline_rates=Rates(**eval_result.baseline_rates),
            notification_sent=sent,
            reason=eval_result.reason,
        )

    @app.get("/metrics", response_model=MetricsResponse, dependencies=[Depends(api_key_guard)])
    async def metrics() -> MetricsResponse:
        return MetricsResponse(rows=app.state.metrics_rows)

    @app.get("/alerts", response_model=AlertsResponse, dependencies=[Depends(api_key_guard)])
    async def alerts() -> AlertsResponse:
        return AlertsResponse(alerts=state.alert_history)

    @app.get("/decision", response_model=DecisionResponse, dependencies=[Depends(api_key_guard)])
    async def decision() -> DecisionResponse:
        return await state.decision_engine.build_response(
            metrics_rows=app.state.metrics_rows,
            alert_history=state.alert_history,
            auth_codes_by_timestamp=state.auth_codes_by_timestamp,
        )

    return app


app = create_app()
