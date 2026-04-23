from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _settings(api_key: str | None = None, **overrides) -> Settings:
    return Settings(
        data_dir=overrides.get("data_dir", Path("database")),
        host=overrides.get("host", "127.0.0.1"),
        port=overrides.get("port", 8000),
        monitoring_api_key=api_key,
        team_notification_webhook_url=overrides.get("team_notification_webhook_url"),
        team_notification_timeout_seconds=overrides.get("team_notification_timeout_seconds", 5.0),
        max_monitor_request_bytes=overrides.get("max_monitor_request_bytes", 65536),
        max_count_value=overrides.get("max_count_value", 1_000_000),
        max_auth_code_keys=overrides.get("max_auth_code_keys", 32),
        max_auth_code_key_length=overrides.get("max_auth_code_key_length", 16),
        minimum_total_count=overrides.get("minimum_total_count", 80),
        minimum_metric_count=overrides.get("minimum_metric_count", 3),
        baseline_window_minutes=overrides.get("baseline_window_minutes", 60),
        cooldown_minutes=overrides.get("cooldown_minutes", 10),
        floor_rate_denied=overrides.get("floor_rate_denied", 0.08),
        floor_rate_failed=overrides.get("floor_rate_failed", 0.02),
        floor_rate_reversed=overrides.get("floor_rate_reversed", 0.03),
        warning_multiplier=overrides.get("warning_multiplier", 2.0),
        critical_multiplier=overrides.get("critical_multiplier", 3.0),
        decision_engine_mode=overrides.get("decision_engine_mode", "local"),
        decision_lookback_minutes=overrides.get("decision_lookback_minutes", 15),
        decision_forecast_horizon_minutes=overrides.get("decision_forecast_horizon_minutes", 30),
        decision_forecast_step_minutes=overrides.get("decision_forecast_step_minutes", 5),
        decision_min_history_points=overrides.get("decision_min_history_points", 5),
        external_ai_provider=overrides.get("external_ai_provider"),
        external_ai_model=overrides.get("external_ai_model"),
        external_ai_api_key=overrides.get("external_ai_api_key"),
        external_ai_base_url=overrides.get("external_ai_base_url"),
        external_ai_timeout_seconds=overrides.get("external_ai_timeout_seconds", 10.0),
    )


def _payload(ts: str, **overrides):
    payload = {
        "window_end": ts,
        "approved": 120,
        "denied": 5,
        "failed": 1,
        "reversed": 1,
        "backend_reversed": 1,
        "refunded": 1,
    }
    payload.update(overrides)
    return payload


def _target_for_panel(dashboard: dict, panel_id: int) -> dict:
    panel = next((panel for panel in dashboard.get("panels", []) if panel.get("id") == panel_id), None)
    assert panel is not None
    targets = panel.get("targets", [])
    assert targets
    return targets[0]


def _has_column(columns: list[dict], text: str, col_type: str) -> bool:
    return any(col.get("text") == text and col.get("type") == col_type for col in columns)

def _panel_by_id(dashboard: dict, panel_id: int) -> dict:
    panel = next((panel for panel in dashboard.get("panels", []) if panel.get("id") == panel_id), None)
    assert panel is not None
    return panel

def _has_percent_override(panel: dict, field_name: str) -> bool:
    for override in panel.get("fieldConfig", {}).get("overrides", []):
        matcher = override.get("matcher", {})
        if matcher.get("id") != "byName" or matcher.get("options") != field_name:
            continue
        for prop in override.get("properties", []):
            if prop.get("id") == "unit" and prop.get("value") == "percentunit":
                return True
    return False


def _priority_snapshot(items: list[dict]) -> list[dict]:
    fields = (
        "metric",
        "decision_status",
        "current_severity",
        "forecast_severity",
        "risk_score",
        "confidence",
        "current_rate",
        "baseline_rate",
        "forecast_rate",
        "above_normal_rate",
        "forecast_above_normal_rate",
        "excess_transactions_now",
        "projected_excess_transactions_horizon",
        "warning_gap_rate",
        "domain_label",
        "likely_owner",
        "recommended_action",
        "root_cause_hint",
        "top_auth_codes",
        "top_auth_codes_display",
    )
    return [{field: item.get(field) for field in fields} for item in items]


def test_health_is_public():
    client = TestClient(create_app(_settings(api_key="secret")))
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_protected_endpoints_require_api_key():
    client = TestClient(create_app(_settings(api_key="secret")))
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics/focus").status_code == 401
    assert client.get("/metrics/recent").status_code == 401
    assert client.get("/alerts").status_code == 401
    assert client.get("/decision").status_code == 401
    assert client.get("/decision/focus").status_code == 401
    assert client.get("/decision/forecast/focus").status_code == 401
    assert client.post("/monitor", json=_payload("2025-07-12 14:00:00")).status_code == 401
    assert client.post("/monitor/transaction", json={"timestamp": "2025-07-12 14:00:00", "status": "approved"}).status_code == 401


def test_valid_api_key_allows_access():
    client = TestClient(create_app(_settings(api_key="secret")))
    headers = {"X-API-Key": "secret"}
    assert client.get("/metrics", headers=headers).status_code == 200
    assert client.get("/metrics/focus", headers=headers).status_code == 200
    assert client.get("/metrics/recent", headers=headers).status_code == 200
    assert client.get("/alerts", headers=headers).status_code == 200
    assert client.get("/decision", headers=headers).status_code == 200
    assert client.get("/decision/focus", headers=headers).status_code == 200
    assert client.get("/decision/forecast/focus", headers=headers).status_code == 200


def test_monitor_contract_and_422():
    client = TestClient(create_app(_settings()))
    bad = _payload("2025-07-12 14:00:00")
    bad["denied"] = "oops"
    resp = client.post("/monitor", json=bad)
    assert resp.status_code == 422

    ok = client.post("/monitor", json=_payload("2025-07-12 14:00:00"))
    assert ok.status_code == 200
    body = ok.json()
    assert "recommendation" in body
    assert "severity" in body
    assert "rates" in body
    assert "baseline_rates" in body
    assert body["team_notification_status"] == "disabled"
    assert body["notification_channels"] == []


def test_low_volume_suppression():
    client = TestClient(create_app(_settings()))
    resp = client.post(
        "/monitor",
        json=_payload("2025-07-12 14:01:00", approved=10, denied=3, failed=0, reversed=0, backend_reversed=0, refunded=0),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommendation"] == "no_alert"


def test_known_dataset_spikes_alert():
    client = TestClient(create_app(_settings()))
    denied_spike = client.post(
        "/monitor",
        json=_payload("2025-07-12 17:18:00", approved=100, denied=54, failed=1, reversed=1, backend_reversed=1, refunded=1),
    )
    assert denied_spike.status_code == 200
    assert denied_spike.json()["recommendation"] == "alert"
    assert "denied" in denied_spike.json()["triggered_metrics"]

    failed_spike = client.post(
        "/monitor",
        json=_payload("2025-07-15 04:30:00", approved=80, denied=4, failed=10, reversed=1, backend_reversed=1, refunded=1),
    )
    assert failed_spike.status_code == 200
    assert failed_spike.json()["recommendation"] == "alert"
    assert "failed" in failed_spike.json()["triggered_metrics"]

    reversed_spike = client.post(
        "/monitor",
        json=_payload("2025-07-14 06:33:00", approved=90, denied=4, failed=1, reversed=7, backend_reversed=1, refunded=1),
    )
    assert reversed_spike.status_code == 200
    assert reversed_spike.json()["recommendation"] == "alert"
    assert "reversed" in reversed_spike.json()["triggered_metrics"]


def test_cooldown_dedup_and_alert_history():
    client = TestClient(create_app(_settings()))
    payload = _payload("2025-07-12 17:18:00", approved=100, denied=54, failed=1, reversed=1, backend_reversed=1, refunded=1)
    first = client.post("/monitor", json=payload).json()
    second = client.post("/monitor", json=payload).json()
    assert first["recommendation"] == "alert"
    assert second["recommendation"] == "no_alert"

    alerts_resp = client.get("/alerts")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()["alerts"]
    assert len(alerts) >= 1
    assert alerts[0]["notification_status"] == "sent"


def test_payload_limits():
    client = TestClient(create_app(_settings()))
    too_many_codes = {f"{i:02d}": 1 for i in range(33)}
    resp = client.post("/monitor", json=_payload("2025-07-12 15:00:00", auth_code_counts=too_many_codes))
    assert resp.status_code == 422

    too_large = client.post("/monitor", json=_payload("2025-07-12 15:00:00", denied=1_000_001))
    assert too_large.status_code == 422


def test_payload_size_limit_returns_422():
    client = TestClient(create_app(_settings(max_monitor_request_bytes=100)))
    large_raw = json.dumps(_payload("2025-07-12 15:00:00", auth_code_counts={f"{i:02d}": 1 for i in range(20)}))
    resp = client.post("/monitor", content=large_raw, headers={"content-type": "application/json"})
    assert resp.status_code == 422


def test_transaction_payload_size_limit_returns_422():
    client = TestClient(create_app(_settings(max_monitor_request_bytes=30)))
    raw = json.dumps({"timestamp": "2025-07-12 15:00:00", "status": "approved", "auth_code": "1234567890"})
    resp = client.post("/monitor/transaction", content=raw, headers={"content-type": "application/json"})
    assert resp.status_code == 422


def test_malformed_content_length_fails_safely():
    client = TestClient(create_app(_settings()))
    resp = client.post(
        "/monitor",
        content=json.dumps(_payload("2025-07-12 15:00:00")),
        headers={"content-type": "application/json", "content-length": "bad-length"},
    )
    assert resp.status_code == 422
    assert "content-length" in resp.json()["detail"].lower()


def test_metrics_shape():
    client = TestClient(create_app(_settings()))
    resp = client.get("/metrics")
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    assert rows
    first = rows[0]
    for key in ["timestamp", "total", "approved_rate", "denied_rate", "failed_rate", "reversed_rate", "alert_severity"]:
        assert key in first


def test_metrics_recent_defaults_to_last_five_days_from_latest():
    client = TestClient(create_app(_settings()))
    resp = client.get("/metrics/recent")
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    assert rows
    timestamps = [row["timestamp"] for row in rows]
    latest = max(timestamps)
    earliest = min(timestamps)
    assert latest == "2025-07-15T13:44:00"
    # Dataset spans ~3 days, so default 5-day window still includes seed range.
    assert earliest == "2025-07-12T13:45:00"


def test_metrics_recent_days_parameter_and_bounds():
    client = TestClient(create_app(_settings()))
    one_day = client.get("/metrics/recent?days=1")
    assert one_day.status_code == 200
    rows = one_day.json()["rows"]
    assert rows
    timestamps = [row["timestamp"] for row in rows]
    assert min(timestamps) == "2025-07-14T13:44:00"
    assert max(timestamps) == "2025-07-15T13:44:00"

    assert client.get("/metrics/recent?days=0").status_code == 422
    assert client.get("/metrics/recent?days=366").status_code == 422


def test_metrics_focus_hourly_aggregates_selected_cluster():
    client = TestClient(create_app(_settings()))
    response = client.get("/metrics/focus?bucket=hour")
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows
    assert rows[0]["timestamp"] == "2025-07-12T13:00:00"
    assert rows[-1]["timestamp"] == "2025-07-15T13:00:00"
    assert len(rows) < 100


def test_metrics_focus_minute_returns_selected_cluster_rows():
    client = TestClient(create_app(_settings()))
    response = client.get("/metrics/focus?bucket=minute")
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows
    assert rows[0]["timestamp"] == "2025-07-12T13:45:00"
    assert rows[-1]["timestamp"] == "2025-07-15T13:44:00"


def test_metrics_focus_invalid_bucket_returns_422():
    client = TestClient(create_app(_settings()))
    assert client.get("/metrics/focus?bucket=day").status_code == 422


def test_decision_shape_local_mode():
    client = TestClient(create_app(_settings()))
    resp = client.get("/decision")
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_status"] in {"normal", "watch", "act_now"}
    assert isinstance(body["priority_items"], list)
    assert len(body["priority_items"]) == 3
    assert "top_auth_codes_display" in body["priority_items"][0]
    assert "problem_explanation" in body
    assert "forecast_explanation" in body
    assert "business_impact" in body
    assert "above_normal_rate" in body["priority_items"][0]
    assert "warning_gap_rate" in body["priority_items"][0]
    assert isinstance(body["forecast_points"], list)
    assert isinstance(body["recent_evidence"], list)
    assert "auth_code_top_display" in body["recent_evidence"][0]
    assert body["provider_status"]["mode"] == "local"
    assert body["provider_status"]["fallback_active"] is False


def test_decision_focus_matches_seeded_cluster_window():
    client = TestClient(create_app(_settings()))
    body = client.get("/decision/focus").json()
    assert body["forecast_points"]
    assert body["recent_evidence"][0]["timestamp"] == "2025-07-15T13:44:00"


def test_decision_forecast_focus_returns_relative_horizon_chart():
    cfg = _settings(decision_forecast_horizon_minutes=30, decision_forecast_step_minutes=5)
    client = TestClient(create_app(cfg))
    body = client.get("/decision/forecast/focus").json()
    points = body["points"]
    assert len(points) == 6
    assert [point["minutes_ahead"] for point in points] == [5, 10, 15, 20, 25, 30]
    assert [point["horizon_label"] for point in points] == ["+5m", "+10m", "+15m", "+20m", "+25m", "+30m"]
    assert all(point["anchor_timestamp"] == "2025-07-15T13:44:00" for point in points)
    assert any(point["denied_rate"] is not None for point in points)
    assert any(point["failed_rate"] is not None for point in points)
    assert any(point["reversed_rate"] is not None for point in points)
    for point in points:
        series_rates = [point["denied_rate"], point["failed_rate"], point["reversed_rate"]]
        populated_rates = [rate for rate in series_rates if rate is not None]
        assert populated_rates
        assert point["max_rate"] == max(populated_rates)


def test_decision_forecast_focus_empty_when_history_is_insufficient():
    client = TestClient(create_app(_settings(decision_min_history_points=999)))
    body = client.get("/decision/forecast/focus").json()
    assert body == {"points": []}


def test_decision_mapping_watch_without_formal_alert():
    cfg = _settings(floor_rate_denied=0.2, warning_multiplier=10.0, critical_multiplier=20.0)
    client = TestClient(create_app(cfg))
    monitor_resp = client.post(
        "/monitor",
        json=_payload("2025-07-16 00:01:00", approved=80, denied=17, failed=1, reversed=1, backend_reversed=1, refunded=0),
    )
    assert monitor_resp.status_code == 200
    assert monitor_resp.json()["recommendation"] == "no_alert"

    decision = client.get("/decision").json()
    assert decision["overall_status"] == "watch"
    alerts = client.get("/alerts").json()["alerts"]
    assert len(alerts) == 0


def test_decision_mapping_act_now_for_alerting_window():
    client = TestClient(create_app(_settings()))
    client.post(
        "/monitor",
        json=_payload("2030-01-01 00:00:00", approved=100, denied=54, failed=1, reversed=1, backend_reversed=1, refunded=1),
    )
    decision = client.get("/decision")
    assert decision.status_code == 200
    assert decision.json()["overall_status"] == "act_now"


def test_forecast_degrades_with_limited_history():
    client = TestClient(create_app(_settings(decision_min_history_points=999)))
    body = client.get("/decision").json()
    assert body["forecast_points"] == []
    for item in body["priority_items"]:
        assert item["forecast_rate"] is None


def test_forecast_warning_when_min_history_is_test_mode_one():
    client = TestClient(create_app(_settings(decision_min_history_points=1)))
    body = client.get("/decision").json()
    assert "for test/demo purposes only" in body["forecast_explanation"]
    assert "recommended setting is 5" in body["forecast_explanation"]


def test_external_mode_unconfigured_falls_back_safely():
    cfg = _settings(decision_engine_mode="external")
    client = TestClient(create_app(cfg))
    body = client.get("/decision").json()
    provider = body["provider_status"]
    assert provider["mode"] == "external"
    assert provider["fallback_active"] is True
    assert provider["last_error"] == "External provider is not fully configured."


def test_external_provider_failure_is_sanitized(monkeypatch):
    cfg = _settings(
        decision_engine_mode="external",
        external_ai_provider="openai",
        external_ai_model="gpt-4.1-mini",
        external_ai_api_key="sk-test-secret",
    )
    app = create_app(cfg)

    async def _boom(*args, **kwargs):
        raise RuntimeError("provider failed with key sk-test-secret and raw payload dump")

    monkeypatch.setattr(app.state.runtime.decision_engine, "_call_external_provider", _boom)
    client = TestClient(app)
    body = client.get("/decision").json()
    provider = body["provider_status"]
    assert provider["fallback_active"] is True
    assert provider["last_error"] == "External provider request failed."
    assert "sk-test-secret" not in (provider["last_error"] or "")


def test_external_provider_success_rewrites_narrative_only(monkeypatch):
    local_client = TestClient(create_app(_settings(decision_engine_mode="local")))
    local_decision = local_client.get("/decision").json()

    cfg = _settings(
        decision_engine_mode="external",
        external_ai_provider="openai",
        external_ai_model="gpt-4.1-mini",
        external_ai_api_key="sk-test-secret",
    )
    app = create_app(cfg)

    async def _ok(*args, **kwargs):
        return json.dumps(
            {
                "summary": "External summary rewrite for operators.",
                "top_recommendation": "External recommendation rewrite only.",
                "problem_explanation": "External problem explanation rewrite.",
                "forecast_explanation": "External forecast explanation rewrite.",
            }
        )

    monkeypatch.setattr(app.state.runtime.decision_engine, "_call_external_provider", _ok)
    external_client = TestClient(app)
    external_decision = external_client.get("/decision").json()

    assert external_decision["summary"] == "External summary rewrite for operators."
    assert external_decision["top_recommendation"] == "External recommendation rewrite only."
    assert external_decision["problem_explanation"] == "External problem explanation rewrite."
    assert external_decision["forecast_explanation"] == "External forecast explanation rewrite."
    assert external_decision["overall_status"] == local_decision["overall_status"]
    assert _priority_snapshot(external_decision["priority_items"]) == _priority_snapshot(local_decision["priority_items"])


def test_openai_compatible_base_url_supports_v1_root():
    cfg = _settings(
        decision_engine_mode="external",
        external_ai_provider="openai",
        external_ai_model="gpt-4.1-mini",
        external_ai_api_key="sk-test-secret",
        external_ai_base_url="https://openrouter.ai/api/v1",
    )
    app = create_app(cfg)
    engine = app.state.runtime.decision_engine
    assert engine._openai_chat_completions_endpoint() == "https://openrouter.ai/api/v1/chat/completions"


def test_openai_compatible_base_url_accepts_full_chat_completions_path():
    cfg = _settings(
        decision_engine_mode="external",
        external_ai_provider="openai",
        external_ai_model="gpt-4.1-mini",
        external_ai_api_key="sk-test-secret",
        external_ai_base_url="https://gateway.example.com/v1/chat/completions",
    )
    app = create_app(cfg)
    engine = app.state.runtime.decision_engine
    assert engine._openai_chat_completions_endpoint() == "https://gateway.example.com/v1/chat/completions"


def test_decision_business_impact_fields_and_projection_clamp():
    client = TestClient(create_app(_settings()))
    decision = client.get("/decision").json()
    impact = decision["business_impact"]
    assert impact["top_metric"] in {"denied", "failed", "reversed"}
    for key in [
        "domain_label",
        "likely_owner",
        "above_normal_rate",
        "warning_gap_rate",
        "excess_transactions_now",
        "projected_excess_transactions_horizon",
    ]:
        assert key in impact

    item = decision["priority_items"][0]
    assert item["above_normal_rate"] >= 0
    assert item["warning_gap_rate"] >= 0
    if item["forecast_above_normal_rate"] is not None:
        assert item["forecast_above_normal_rate"] >= 0


def test_decision_explains_elevated_but_not_alerting_window():
    cfg = _settings(floor_rate_denied=0.2, warning_multiplier=10.0, critical_multiplier=20.0)
    client = TestClient(create_app(cfg))
    client.post(
        "/monitor",
        json=_payload("2025-07-16 00:01:00", approved=80, denied=17, failed=1, reversed=1, backend_reversed=1, refunded=0),
    )
    decision = client.get("/decision").json()
    assert decision["overall_status"] == "watch"
    assert "above baseline" in decision["problem_explanation"].lower()
    assert "below formal warning" in decision["problem_explanation"].lower()


def test_logging_safety_and_no_raw_payload():
    client = TestClient(create_app(_settings()))
    payload = _payload(
        "2025-07-12 17:18:00",
        approved=100,
        denied=54,
        failed=1,
        reversed=1,
        backend_reversed=1,
        refunded=1,
        auth_code_counts={"00": 100, "59": 54},
    )
    client.post("/monitor", json=payload)
    log_text = Path("logs/alerts.log").read_text(encoding="utf-8")
    assert "MONITORING_API_KEY" not in log_text
    assert "auth_code_counts" not in log_text


def test_team_notification_status_disabled_by_default():
    client = TestClient(
        create_app(
            _settings(
                minimum_total_count=1,
                minimum_metric_count=1,
                floor_rate_denied=0.01,
                warning_multiplier=1.0,
                critical_multiplier=2.0,
            )
        )
    )
    response = client.post("/monitor", json=_payload("2025-07-12 17:18:00", approved=1, denied=1, failed=0, reversed=0, backend_reversed=0, refunded=0))
    body = response.json()
    assert body["recommendation"] == "alert"
    assert body["notification_sent"] is True
    assert body["team_notification_status"] == "disabled"
    assert body["notification_channels"] == ["log"]
    alert = client.get("/alerts").json()["alerts"][0]
    assert alert["notification_status"] == "sent"
    assert alert["team_notification_status"] == "disabled"
    assert alert["notification_channels"] == ["log"]


def test_team_notification_webhook_success(monkeypatch):
    cfg = _settings(
        team_notification_webhook_url="http://notify.example/notify",
        minimum_total_count=1,
        minimum_metric_count=1,
        floor_rate_denied=0.01,
        warning_multiplier=1.0,
        critical_multiplier=2.0,
    )

    def _ok(url, json, timeout):
        assert url == "http://notify.example/notify"
        assert "auth_code_top" in json
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.notifier.httpx.post", _ok)
    client = TestClient(create_app(cfg))
    response = client.post(
        "/monitor",
        json=_payload("2025-07-12 17:18:00", approved=1, denied=1, failed=0, reversed=0, backend_reversed=0, refunded=0, auth_code_counts={"51": 1}),
    )
    body = response.json()
    assert body["team_notification_status"] == "sent"
    assert body["notification_channels"] == ["log", "webhook"]
    alert = client.get("/alerts").json()["alerts"][0]
    assert alert["team_notification_status"] == "sent"
    assert alert["notification_channels"] == ["log", "webhook"]


def test_team_notification_webhook_failure(monkeypatch):
    cfg = _settings(
        team_notification_webhook_url="http://notify.example/notify",
        minimum_total_count=1,
        minimum_metric_count=1,
        floor_rate_denied=0.01,
        warning_multiplier=1.0,
        critical_multiplier=2.0,
    )

    def _boom(url, json, timeout):
        raise httpx.ConnectError("connect failed", request=httpx.Request("POST", url))

    monkeypatch.setattr("app.notifier.httpx.post", _boom)
    client = TestClient(create_app(cfg))
    response = client.post("/monitor", json=_payload("2025-07-12 17:18:00", approved=1, denied=1, failed=0, reversed=0, backend_reversed=0, refunded=0))
    body = response.json()
    assert body["team_notification_status"] == "failed"
    assert body["notification_channels"] == ["log", "webhook"]
    alert = client.get("/alerts").json()["alerts"][0]
    assert alert["team_notification_status"] == "failed"
    assert alert["notification_channels"] == ["log", "webhook"]


def test_team_notification_webhook_timeout(monkeypatch):
    cfg = _settings(
        team_notification_webhook_url="http://notify.example/notify",
        minimum_total_count=1,
        minimum_metric_count=1,
        floor_rate_denied=0.01,
        warning_multiplier=1.0,
        critical_multiplier=2.0,
    )

    def _timeout(url, json, timeout):
        raise httpx.ReadTimeout("timed out", request=httpx.Request("POST", url))

    monkeypatch.setattr("app.notifier.httpx.post", _timeout)
    client = TestClient(create_app(cfg))
    response = client.post("/monitor", json=_payload("2025-07-12 17:18:00", approved=1, denied=1, failed=0, reversed=0, backend_reversed=0, refunded=0))
    body = response.json()
    assert body["team_notification_status"] == "failed"
    assert body["notification_channels"] == ["log", "webhook"]
    alert = client.get("/alerts").json()["alerts"][0]
    assert alert["team_notification_status"] == "failed"
    assert alert["notification_channels"] == ["log", "webhook"]


def test_auth_code_fallback_from_dataset():
    client = TestClient(create_app(_settings()))
    payload = _payload(
        "2025-07-12 17:18:00",
        approved=100,
        denied=54,
        failed=1,
        reversed=1,
        backend_reversed=1,
        refunded=1,
    )
    client.post("/monitor", json=payload)
    alerts_resp = client.get("/alerts")
    alerts = alerts_resp.json()["alerts"]
    assert alerts
    assert alerts[0]["auth_code_top"]
    assert alerts[0]["auth_code_top_display"]
    assert "00 Approved" in alerts[0]["auth_code_top_display"]
    codes = [item[0] for item in alerts[0]["auth_code_top"]]
    assert "00" in codes


def test_transaction_event_endpoint_aggregates_minute_bucket():
    cfg = _settings(
        minimum_total_count=1,
        minimum_metric_count=1,
        floor_rate_denied=0.01,
        warning_multiplier=1.0,
        critical_multiplier=2.0,
    )
    app = create_app(cfg)
    client = TestClient(app)

    first = client.post("/monitor/transaction", json={"timestamp": "2025-07-16 00:00:12", "status": "approved"})
    second = client.post("/monitor/transaction", json={"timestamp": "2025-07-16 00:00:35", "status": "denied", "auth_code": "51"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["window_end"].startswith("2025-07-16T00:00:00")
    row = next(row for row in app.state.runtime.rows if row.timestamp.isoformat() == "2025-07-16T00:00:00")
    assert row.counts["approved"] == 1
    assert row.counts["denied"] == 1
    assert row.auth_code_counts == {"51": 1}


def test_transaction_event_endpoint_enforces_auth_code_length():
    client = TestClient(create_app(_settings()))
    response = client.post(
        "/monitor/transaction",
        json={"timestamp": "2025-07-16 00:00:35", "status": "denied", "auth_code": "12345678901234567"},
    )
    assert response.status_code == 422


def test_transaction_event_endpoint_rejects_unsupported_status():
    client = TestClient(create_app(_settings()))
    response = client.post(
        "/monitor/transaction",
        json={"timestamp": "2025-07-16 00:00:35", "status": "not-a-valid-status"},
    )
    assert response.status_code == 422


def test_auth_code_display_fields_format_known_and_unknown_codes():
    client = TestClient(create_app(_settings()))
    client.post(
        "/monitor",
        json=_payload(
            "2030-01-01 00:00:00",
            approved=100,
            denied=54,
            failed=1,
            reversed=1,
            backend_reversed=1,
            refunded=1,
            auth_code_counts={"51": 6, "XX": 4, "59": 3},
        ),
    )

    alerts = client.get("/alerts").json()["alerts"]
    assert alerts[0]["auth_code_top_display"] == "51 Insufficient funds x6, XX Unknown x4, 59 Suspected fraud x3"

    decision = client.get("/decision").json()
    priority_item = next(item for item in decision["priority_items"] if item["metric"] == "denied")
    assert priority_item["top_auth_codes"] == [["51", 6], ["XX", 4], ["59", 3]]
    assert priority_item["top_auth_codes_display"] == "51 Insufficient funds x6, XX Unknown x4, 59 Suspected fraud x3"

    evidence = next(item for item in decision["recent_evidence"] if item["source"] == "metrics")
    assert evidence["auth_code_top_display"] == "51 Insufficient funds x6, XX Unknown x4, 59 Suspected fraud x3"


def test_metrics_realtime_upsert_after_monitor():
    client = TestClient(create_app(_settings()))
    before = client.get("/metrics").json()["rows"]
    ts = "2025-07-16 00:00:00"
    client.post(
        "/monitor",
        json=_payload(ts, approved=90, denied=15, failed=3, reversed=2, backend_reversed=1, refunded=1),
    )
    after = client.get("/metrics").json()["rows"]
    assert len(after) >= len(before)
    found = [row for row in after if row["timestamp"].startswith("2025-07-16T00:00:00")]
    assert found


def test_dashboard_render_ignores_singleton_newer_point_until_cluster_is_eligible():
    app = create_app(_settings())
    client = TestClient(app)
    dashboard_before = json.loads(Path("grafana/dashboard.json").read_text(encoding="utf-8"))
    assert dashboard_before["time"] == {"from": "2025-07-12T13:45:00Z", "to": "2025-07-15T14:14:00Z"}

    client.post(
        "/monitor",
        json=_payload("2026-04-23 12:00:00", approved=100, denied=10, failed=1, reversed=1, backend_reversed=0, refunded=0),
    )
    dashboard_after = json.loads(Path("grafana/dashboard.json").read_text(encoding="utf-8"))
    assert dashboard_after["time"] == dashboard_before["time"]


def test_dashboard_render_moves_to_newer_eligible_cluster():
    app = create_app(_settings())
    client = TestClient(app)
    for idx in range(5):
        minute = f"2026-04-23 12:0{idx}:00"
        response = client.post(
            "/monitor",
            json=_payload(minute, approved=100, denied=10 + idx, failed=1, reversed=1, backend_reversed=0, refunded=0),
        )
        assert response.status_code == 200

    dashboard = json.loads(Path("grafana/dashboard.json").read_text(encoding="utf-8"))
    assert dashboard["time"] == {"from": "2026-04-23T12:00:00Z", "to": "2026-04-23T12:34:00Z"}


def test_api_key_guard_uses_constant_time_compare():
    source = Path("app/security.py").read_text(encoding="utf-8")
    assert "compare_digest" in source
    assert "not compare_digest(" in source


def test_dashboard_contract_for_decision_first_panels():
    create_app(_settings())
    dashboard = json.loads(Path("grafana/dashboard.json").read_text(encoding="utf-8"))
    assert dashboard.get("time") == {"from": "2025-07-12T13:45:00Z", "to": "2025-07-15T14:14:00Z"}
    titles = {panel.get("title") for panel in dashboard.get("panels", [])}
    assert "What Needs Attention Right Now" in titles
    assert "Why Each Metric Is Ranked This Way" in titles
    assert "What Could Get Worse In The Forecast Window" in titles
    assert "Evidence Behind The Current Recommendation" in titles
    assert "Formal Alerts That Have Already Fired" in titles
    assert "What This Top Issue Means For The Business" in titles
    assert "How Risk Rates Are Moving Over Time" in titles
    assert "How Much Traffic These Rates Represent" in titles
    assert "How To Read This Dashboard On First Login" in titles

    panel1 = _target_for_panel(dashboard, 1)
    assert panel1["format"] == "table"
    assert panel1["parser"] == "backend"
    assert panel1["url"] == "http://api:8000/decision/focus"
    assert _has_column(panel1.get("columns", []), "Decision generated at", "timestamp")
    assert _has_column(panel1.get("columns", []), "Overall status right now", "string")
    assert _has_column(panel1.get("columns", []), "What the reviewer should do next", "string")
    assert _has_column(panel1.get("columns", []), "Why this issue is ranked first", "string")
    assert _has_column(panel1.get("columns", []), "What is above normal and why it matters", "string")
    assert _has_column(panel1.get("columns", []), "What may happen next", "string")

    panel3 = _target_for_panel(dashboard, 3)
    assert panel3["format"] == "table"
    assert panel3["parser"] == "backend"
    assert panel3["url"] == "http://api:8000/decision/forecast/focus"
    assert _has_column(panel3.get("columns", []), "Forecast horizon", "string")
    assert _has_column(panel3.get("columns", []), "Denied rate (%)", "number")
    assert _has_column(panel3.get("columns", []), "Failed rate (%)", "number")
    assert _has_column(panel3.get("columns", []), "Reversed rate (%)", "number")
    assert _panel_by_id(dashboard, 3).get("fieldConfig", {}).get("defaults", {}).get("unit") == "percentunit"
    assert _panel_by_id(dashboard, 3).get("type") == "barchart"

    panel2 = _target_for_panel(dashboard, 2)
    assert panel2["format"] == "table"
    assert panel2["parser"] == "backend"
    assert panel2["url"] == "http://api:8000/decision/focus"
    assert _has_column(panel2.get("columns", []), "Metric under review", "string")
    assert _has_column(panel2.get("columns", []), "Action level now", "string")
    assert _has_column(panel2.get("columns", []), "Formal alert severity now", "string")
    assert _has_column(panel2.get("columns", []), "Priority score (0-100)", "number")
    assert _has_column(panel2.get("columns", []), "Confidence in this ranking (%)", "number")
    assert _has_column(panel2.get("columns", []), "Current rate now (%)", "number")
    assert _has_column(panel2.get("columns", []), "Typical baseline rate (%)", "number")
    assert _has_column(panel2.get("columns", []), "Forecast rate within horizon (%)", "number")
    assert _has_column(panel2.get("columns", []), "Top authorization-code clues", "string")
    assert _has_column(panel2.get("columns", []), "Above baseline now (percentage points)", "number")
    assert _has_column(panel2.get("columns", []), "Above baseline within forecast horizon (percentage points)", "number")
    assert _has_column(panel2.get("columns", []), "Gap before formal warning (percentage points remaining)", "number")
    assert _has_column(panel2.get("columns", []), "Extra affected transactions now (approx.)", "number")
    assert _has_column(panel2.get("columns", []), "Extra affected transactions within forecast horizon (approx.)", "number")
    assert _has_column(panel2.get("columns", []), "Business area affected", "string")
    assert _has_column(panel2.get("columns", []), "Team likely to act", "string")
    assert _has_column(panel2.get("columns", []), "Recommended next step", "string")
    panel2_full = _panel_by_id(dashboard, 2)
    assert _has_percent_override(panel2_full, "Confidence in this ranking (%)")
    assert _has_percent_override(panel2_full, "Current rate now (%)")
    assert _has_percent_override(panel2_full, "Typical baseline rate (%)")
    assert _has_percent_override(panel2_full, "Forecast rate within horizon (%)")
    assert _has_percent_override(panel2_full, "Above baseline now (percentage points)")
    assert _has_percent_override(panel2_full, "Above baseline within forecast horizon (percentage points)")
    assert _has_percent_override(panel2_full, "Gap before formal warning (percentage points remaining)")

    panel4 = _target_for_panel(dashboard, 4)
    assert panel4["url"] == "http://api:8000/decision/focus"
    assert _has_column(panel4.get("columns", []), "Recorded at", "timestamp")
    assert _has_column(panel4.get("columns", []), "Evidence source", "string")
    assert _has_column(panel4.get("columns", []), "What this evidence says", "string")
    assert _has_column(panel4.get("columns", []), "Supporting authorization-code context", "string")

    panel5 = _target_for_panel(dashboard, 5)
    assert panel5["format"] == "table"
    assert panel5["parser"] == "backend"
    assert panel5["url"] == "http://api:8000/alerts"
    assert _has_column(panel5.get("columns", []), "Recorded at", "timestamp")
    assert _has_column(panel5.get("columns", []), "Formal alert severity", "string")
    assert _has_column(panel5.get("columns", []), "Formal alert handling result", "string")
    assert _has_column(panel5.get("columns", []), "Why the formal alert fired", "string")

    panel6 = _target_for_panel(dashboard, 6)
    assert panel6["url"] == "http://api:8000/metrics/focus?bucket=hour"
    assert _panel_by_id(dashboard, 6).get("fieldConfig", {}).get("defaults", {}).get("unit") == "percentunit"

    panel7 = _target_for_panel(dashboard, 7)
    assert panel7["url"] == "http://api:8000/metrics/focus?bucket=hour"
    assert _panel_by_id(dashboard, 7).get("fieldConfig", {}).get("defaults", {}).get("custom", {}).get("drawStyle") == "bars"

    panel9 = _target_for_panel(dashboard, 9)
    assert panel9["url"] == "http://api:8000/decision/focus"
    assert _has_column(panel9.get("columns", []), "Top metric driving the issue", "string")
    assert _has_column(panel9.get("columns", []), "Business area affected", "string")
    assert _has_column(panel9.get("columns", []), "Team likely to act", "string")
    assert _has_column(panel9.get("columns", []), "Above baseline now (percentage points)", "number")
    assert _has_column(panel9.get("columns", []), "Gap before formal warning (percentage points remaining)", "number")
    assert _has_column(panel9.get("columns", []), "Extra affected transactions now (approx.)", "number")
    assert _has_column(panel9.get("columns", []), "Extra affected transactions within forecast horizon (approx.)", "number")
    panel9_full = _panel_by_id(dashboard, 9)
    assert _has_percent_override(panel9_full, "Above baseline now (percentage points)")
    assert _has_percent_override(panel9_full, "Gap before formal warning (percentage points remaining)")


def test_reviewer_bootstrap_contract_and_secret_handling():
    script = Path("scripts/reviewer_start.sh").read_text(encoding="utf-8")
    assert "ENV_FILE=\"${ROOT_DIR}/.env.reviewer\"" in script
    assert "chmod 600 \"${ENV_FILE}\"" in script
    assert "Decision mode (local/external)" in script
    assert "\"Decision mode (local/external)\" \"external\"" in script
    assert "External provider (openai/anthropic/google)" in script
    assert "No external API key provided. Falling back to local deterministic mode." in script
    assert "Local mode remains fully functional for monitoring decisions" in script
    assert "Monitoring API key: configured in %s (MONITORING_API_KEY)" in script
    assert "Local team notification receiver:" in script
    assert "Team notification target:" in script


def test_smoke_script_checks_decision_and_dashboard_contract():
    script = Path("scripts/smoke_one_click.sh").read_text(encoding="utf-8")
    assert "/decision" in script
    assert "Team notification receiver health endpoint" in script
    assert "${TEAM_RECEIVER_URL}/health" in script
    assert "/notifications" in script
    assert "team-notification payload" in script or "Team notification delivery" in script
    assert "python3 scripts/check_grafana_dashboard_contract.py" in script
    assert "./scripts/check_grafana_dashboard_playwright.sh" in script


def test_openspec_wrapper_prefers_project_venv():
    script = Path("scripts/openspec.sh").read_text(encoding="utf-8")
    assert "VENV_OPENSPEC" in script
    assert ".venv/bin/openspec" in script
    assert "exec \"${VENV_OPENSPEC}\" \"$@\"" in script


def test_compose_provisions_team_receiver_and_webhook_default():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "team-receiver:" in compose
    assert "TEAM_NOTIFICATION_WEBHOOK_URL: ${TEAM_NOTIFICATION_WEBHOOK_URL:-http://team-receiver:8010/notify}" in compose
    assert '127.0.0.1:${TEAM_RECEIVER_PORT:-8010}:8010' in compose


def test_checkout_report_acceptance_markers():
    report = Path("report/technical_report.md").read_text(encoding="utf-8")
    assert "08h" in report
    assert "09h" in report
    assert any(marker in report for marker in ["10h", "12h", "15h", "17h"])
    assert "How This Repository Satisfies The Challenge Requirements" in report
    assert "Required monitoring endpoint:" in report
    assert "Required query and real-time graphic:" in report
    assert "Required anomaly model:" in report
    assert "Required automatic reporting:" in report


def test_api_entrypoint_bootstrap_fail_fast_contract():
    entrypoint = Path("docker/api-entrypoint.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in entrypoint
    assert "python -m scripts.checkout_analysis" in entrypoint
    assert "python -m scripts.generate_checkout_charts" in entrypoint
    assert "exec uvicorn app.main:app" in entrypoint
    assert entrypoint.index("python -m scripts.checkout_analysis") < entrypoint.index("exec uvicorn app.main:app")
    assert entrypoint.index("python -m scripts.generate_checkout_charts") < entrypoint.index("exec uvicorn app.main:app")
