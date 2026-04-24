from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException

from app.anomaly import AlertEngine
from app.config import Settings, load_settings
from app.data_loader import HistoricalRow, compute_rates, load_transactions
from app.dashboard_focus import (
    build_metrics_rows as build_dashboard_metrics_rows,
    filter_cluster_alerts,
    focus_metrics_rows,
    render_dashboard,
    select_focus_cluster,
)
from app.decision import DecisionEngine
from app.models import (
    AlertRecord,
    AlertsResponse,
    DecisionResponse,
    ForecastChartResponse,
    MetricsResponse,
    MetricsRow,
    MonitorRequest,
    MonitorResponse,
    Rates,
    TransactionEventRequest,
)
from app.notifier import AlertNotifier
from app.security import MonitorPayloadLimitMiddleware, build_api_key_guard


@dataclass
class RuntimeState:
    rows: list[HistoricalRow]
    engine: AlertEngine
    decision_engine: DecisionEngine
    notifier: AlertNotifier
    auth_codes_by_timestamp: dict[datetime, dict[str, int]] = field(default_factory=dict)
    alert_history: list[AlertRecord] = field(default_factory=list)
    dashboard_render_hash: str | None = None


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
    if timestamp.tzinfo is None:
        return timestamp
    # Convert aware timestamps to a single UTC-naive bucket space.
    return timestamp.astimezone(UTC).replace(tzinfo=None)


def _normalize_minute_bucket(timestamp: datetime) -> datetime:
    normalized = _normalize_timestamp(timestamp)
    return normalized.replace(second=0, microsecond=0)


def _recent_metrics_rows(rows: list[MetricsRow], days: int) -> list[MetricsRow]:
    if not rows:
        return []
    latest_timestamp = max(row.timestamp for row in rows)
    start_timestamp = latest_timestamp - timedelta(days=days)
    return [row for row in rows if start_timestamp <= row.timestamp <= latest_timestamp]


def _sync_dashboard_render(app: FastAPI, state: RuntimeState, cfg: Settings) -> None:
    cluster = select_focus_cluster(state.rows)
    if cluster is None:
        return
    state.dashboard_render_hash = render_dashboard(
        root_dir=app.state.root_dir,
        cluster=cluster,
        decision_min_history_points=cfg.decision_min_history_points,
        decision_forecast_horizon_minutes=cfg.decision_forecast_horizon_minutes,
    )


async def _build_focus_decision_response(state: RuntimeState, *, allow_external_narrative: bool = True) -> DecisionResponse:
    cluster = select_focus_cluster(state.rows)
    if cluster is None:
        return await state.decision_engine.build_response(
            metrics_rows=[],
            alert_history=[],
            auth_codes_by_timestamp={},
            allow_external_narrative=allow_external_narrative,
        )

    focus_alert_history = filter_cluster_alerts(state.alert_history, cluster)
    focus_auth_codes = {
        timestamp: codes
        for timestamp, codes in state.auth_codes_by_timestamp.items()
        if cluster.start <= timestamp <= cluster.end
    }
    return await state.decision_engine.build_response(
        metrics_rows=build_dashboard_metrics_rows(list(cluster.rows), state.engine),
        alert_history=focus_alert_history,
        auth_codes_by_timestamp=focus_auth_codes,
        allow_external_narrative=allow_external_narrative,
    )


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


def _find_historical_row(rows: list[HistoricalRow], timestamp: datetime) -> HistoricalRow | None:
    for row in rows:
        if row.timestamp == timestamp:
            return row
    return None


def _validate_counts(cfg: Settings, counts: dict[str, int]) -> None:
    # Hard limits from security requirements.
    for key, value in counts.items():
        if value > cfg.max_count_value:
            raise HTTPException(status_code=422, detail=f"{key} exceeds max_count_value")


def _top_auth_codes(auth_codes: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(auth_codes.items(), key=lambda kv: kv[1], reverse=True)[:5]


def _apply_monitor_window(
    *,
    app: FastAPI,
    state: RuntimeState,
    cfg: Settings,
    timestamp: datetime,
    counts: dict[str, int],
    auth_code_counts: dict[str, int],
) -> MonitorResponse:
    eval_result = state.engine.evaluate(timestamp, counts, apply_cooldown=True)
    sent = False
    status_text = "skipped"
    team_status = "disabled"
    channels: list[str] = []
    auth_top = _top_auth_codes(auth_code_counts)

    if eval_result.recommendation == "alert":
        notify_result = state.notifier.notify(
            timestamp=timestamp,
            severity=eval_result.severity,
            triggered_metrics=eval_result.triggered_metrics,
            rates=eval_result.rates,
            baseline_rates=eval_result.baseline_rates,
            reason=eval_result.reason,
            auth_code_top=auth_top,
        )
        sent = notify_result.sent
        status_text = notify_result.status
        team_status = notify_result.team_notification_status
        channels = notify_result.notification_channels

        state.alert_history.append(
            AlertRecord(
                timestamp=timestamp,
                severity=eval_result.severity,
                triggered_metrics=eval_result.triggered_metrics,
                rates=Rates(**eval_result.rates),
                baseline_rates=Rates(**eval_result.baseline_rates),
                notification_status=status_text,
                team_notification_status=team_status,
                notification_channels=channels,
                reason=eval_result.reason,
                auth_code_top=auth_top,
            )
        )

    updated_rows = _upsert_historical_row(
        state.rows,
        HistoricalRow(
            timestamp=timestamp,
            counts=counts.copy(),
            auth_code_counts=auth_code_counts,
        ),
    )
    state.rows = updated_rows
    state.auth_codes_by_timestamp[timestamp] = auth_code_counts
    state.engine.historical_rows = updated_rows
    state.engine.global_baseline = state.engine._compute_global_baseline()

    app.state.metrics_rows = _upsert_metrics_row(
        app.state.metrics_rows,
        MetricsRow(
            timestamp=timestamp,
            total=sum(counts.values()),
            approved_rate=round(counts["approved"] / max(1, sum(counts.values())), 6),
            denied_rate=round(eval_result.rates["denied_rate"], 6),
            failed_rate=round(eval_result.rates["failed_rate"], 6),
            reversed_rate=round(eval_result.rates["reversed_rate"], 6),
            alert_severity=eval_result.severity,
        ),
    )
    _sync_dashboard_render(app, state, cfg)

    return MonitorResponse(
        window_end=timestamp,
        recommendation=eval_result.recommendation,
        severity=eval_result.severity,
        triggered_metrics=eval_result.triggered_metrics,
        rates=Rates(**eval_result.rates),
        baseline_rates=Rates(**eval_result.baseline_rates),
        notification_sent=sent,
        team_notification_status=team_status,
        notification_channels=channels,
        reason=eval_result.reason,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    rows = load_transactions(cfg.data_dir)
    notifier = AlertNotifier(
        log_path=Path("logs/alerts.log"),
        webhook_url=cfg.team_notification_webhook_url,
        webhook_timeout_seconds=cfg.team_notification_timeout_seconds,
    )
    engine = AlertEngine(settings=cfg, historical_rows=rows)
    decision_engine = DecisionEngine(settings=cfg, alert_engine=engine)
    state = RuntimeState(rows=rows, engine=engine, decision_engine=decision_engine, notifier=notifier)
    state.auth_codes_by_timestamp = {row.timestamp: row.auth_code_counts for row in rows}
    api_key_guard = build_api_key_guard(cfg.monitoring_api_key)

    app = FastAPI(title="CloudWalk Monitoring Test Submission", version="0.1.0")
    app.add_middleware(MonitorPayloadLimitMiddleware, max_bytes=cfg.max_monitor_request_bytes)
    app.state.runtime = state
    app.state.settings = cfg
    app.state.root_dir = Path(__file__).resolve().parents[1]
    app.state.metrics_rows = build_dashboard_metrics_rows(rows, engine)
    _sync_dashboard_render(app, state, cfg)

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
        _validate_counts(cfg, counts)
        if payload.auth_code_counts and len(payload.auth_code_counts) > cfg.max_auth_code_keys:
            raise HTTPException(status_code=422, detail="auth_code_counts exceeds key limit")
        auth_code_counts = payload.auth_code_counts or state.auth_codes_by_timestamp.get(normalized_window_end, {})
        return _apply_monitor_window(
            app=app,
            state=state,
            cfg=cfg,
            timestamp=normalized_window_end,
            counts=counts,
            auth_code_counts=auth_code_counts,
        )

    @app.post("/monitor/transaction", response_model=MonitorResponse, dependencies=[Depends(api_key_guard)])
    async def monitor_transaction(payload: TransactionEventRequest) -> MonitorResponse:
        minute_bucket = _normalize_minute_bucket(payload.timestamp)
        existing = _find_historical_row(state.rows, minute_bucket)
        counts = existing.counts.copy() if existing is not None else {
            "approved": 0,
            "denied": 0,
            "failed": 0,
            "reversed": 0,
            "backend_reversed": 0,
            "refunded": 0,
        }
        counts[payload.status] = counts.get(payload.status, 0) + 1
        _validate_counts(cfg, counts)

        auth_code_counts = state.auth_codes_by_timestamp.get(minute_bucket, {}).copy()
        if payload.auth_code:
            auth_code_counts[payload.auth_code] = auth_code_counts.get(payload.auth_code, 0) + 1
        if len(auth_code_counts) > cfg.max_auth_code_keys:
            raise HTTPException(status_code=422, detail="auth_code_counts exceeds key limit")

        return _apply_monitor_window(
            app=app,
            state=state,
            cfg=cfg,
            timestamp=minute_bucket,
            counts=counts,
            auth_code_counts=auth_code_counts,
        )

    @app.get("/metrics", response_model=MetricsResponse, dependencies=[Depends(api_key_guard)])
    async def metrics() -> MetricsResponse:
        return MetricsResponse(rows=app.state.metrics_rows)

    @app.get("/metrics/recent", response_model=MetricsResponse, dependencies=[Depends(api_key_guard)])
    async def metrics_recent(days: int = 5) -> MetricsResponse:
        if days < 1 or days > 365:
            raise HTTPException(status_code=422, detail="days must be between 1 and 365")
        return MetricsResponse(rows=_recent_metrics_rows(app.state.metrics_rows, days))

    @app.get("/metrics/focus", response_model=MetricsResponse, dependencies=[Depends(api_key_guard)])
    async def metrics_focus(bucket: Literal["hour", "minute"] = "hour") -> MetricsResponse:
        return MetricsResponse(rows=focus_metrics_rows(state.rows, state.engine, bucket))

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

    @app.get("/decision/focus", response_model=DecisionResponse, dependencies=[Depends(api_key_guard)])
    async def decision_focus() -> DecisionResponse:
        return await _build_focus_decision_response(state)

    @app.get("/decision/forecast/focus", response_model=ForecastChartResponse, dependencies=[Depends(api_key_guard)])
    async def decision_forecast_focus() -> ForecastChartResponse:
        cluster = select_focus_cluster(state.rows)
        if cluster is None:
            return ForecastChartResponse(points=[])

        decision_response = await _build_focus_decision_response(state, allow_external_narrative=False)
        if not decision_response.forecast_points:
            return ForecastChartResponse(points=[])
        return state.decision_engine.build_forecast_chart(
            anchor_timestamp=cluster.end,
            forecast_points=decision_response.forecast_points,
        )

    return app


app = create_app()
