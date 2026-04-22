from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _settings(api_key: str | None = None, **overrides) -> Settings:
    return Settings(
        data_dir=overrides.get("data_dir", Path("database")),
        host=overrides.get("host", "127.0.0.1"),
        port=overrides.get("port", 8000),
        monitoring_api_key=api_key,
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
    assert client.get("/alerts").status_code == 401
    assert client.get("/decision").status_code == 401
    assert client.post("/monitor", json=_payload("2025-07-12 14:00:00")).status_code == 401


def test_valid_api_key_allows_access():
    client = TestClient(create_app(_settings(api_key="secret")))
    headers = {"X-API-Key": "secret"}
    assert client.get("/metrics", headers=headers).status_code == 200
    assert client.get("/alerts", headers=headers).status_code == 200
    assert client.get("/decision", headers=headers).status_code == 200


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


def test_decision_shape_local_mode():
    client = TestClient(create_app(_settings()))
    resp = client.get("/decision")
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_status"] in {"normal", "watch", "act_now"}
    assert isinstance(body["priority_items"], list)
    assert len(body["priority_items"]) == 3
    assert "top_auth_codes_display" in body["priority_items"][0]
    assert isinstance(body["forecast_points"], list)
    assert isinstance(body["recent_evidence"], list)
    assert "auth_code_top_display" in body["recent_evidence"][0]
    assert body["provider_status"]["mode"] == "local"
    assert body["provider_status"]["fallback_active"] is False


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
            }
        )

    monkeypatch.setattr(app.state.runtime.decision_engine, "_call_external_provider", _ok)
    external_client = TestClient(app)
    external_decision = external_client.get("/decision").json()

    assert external_decision["summary"] == "External summary rewrite for operators."
    assert external_decision["top_recommendation"] == "External recommendation rewrite only."
    assert external_decision["overall_status"] == local_decision["overall_status"]
    assert _priority_snapshot(external_decision["priority_items"]) == _priority_snapshot(local_decision["priority_items"])


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


def test_api_key_guard_uses_constant_time_compare():
    source = Path("app/security.py").read_text(encoding="utf-8")
    assert "compare_digest" in source
    assert "not compare_digest(" in source


def test_dashboard_contract_for_decision_first_panels():
    dashboard = json.loads(Path("grafana/dashboard.json").read_text(encoding="utf-8"))
    titles = {panel.get("title") for panel in dashboard.get("panels", [])}
    assert "Decision Snapshot" in titles
    assert "Priority Queue" in titles
    assert "Forecast Risk" in titles
    assert "Recent Evidence" in titles
    assert "Recent Formal Alerts" in titles
    assert "Risk Trend by Metric" in titles
    assert "Transaction Volume Context" in titles
    assert "Reviewer First Login" in titles

    panel1 = _target_for_panel(dashboard, 1)
    assert panel1["format"] == "table"
    assert panel1["parser"] == "backend"
    assert _has_column(panel1.get("columns", []), "generated_at", "timestamp")
    assert _has_column(panel1.get("columns", []), "overall_status", "string")

    panel3 = _target_for_panel(dashboard, 3)
    assert panel3["format"] == "timeseries"
    assert panel3["parser"] == "backend"
    assert _has_column(panel3.get("columns", []), "Time", "timestamp")
    assert _has_column(panel3.get("columns", []), "forecast_rate", "number")

    panel2 = _target_for_panel(dashboard, 2)
    assert _has_column(panel2.get("columns", []), "top_auth_codes_display", "string")

    panel4 = _target_for_panel(dashboard, 4)
    assert _has_column(panel4.get("columns", []), "auth_code_top_display", "string")


def test_reviewer_bootstrap_contract_and_secret_handling():
    script = Path("scripts/reviewer_start.sh").read_text(encoding="utf-8")
    assert "ENV_FILE=\"${ROOT_DIR}/.env.reviewer\"" in script
    assert "chmod 600 \"${ENV_FILE}\"" in script
    assert "Decision mode (local/external)" in script
    assert "External provider (openai/anthropic/google)" in script
    assert "No external API key provided. Falling back to local mode." in script
    assert "Monitoring API key: configured in %s (MONITORING_API_KEY)" in script


def test_smoke_script_checks_decision_and_dashboard_contract():
    script = Path("scripts/smoke_one_click.sh").read_text(encoding="utf-8")
    assert "/decision" in script
    assert "python3 scripts/check_grafana_dashboard_contract.py" in script


def test_checkout_report_acceptance_markers():
    report = Path("report/technical_report.md").read_text(encoding="utf-8")
    assert "08h" in report
    assert "09h" in report
    assert any(marker in report for marker in ["10h", "12h", "15h", "17h"])


def test_api_entrypoint_bootstrap_fail_fast_contract():
    entrypoint = Path("docker/api-entrypoint.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in entrypoint
    assert "python -m scripts.checkout_analysis" in entrypoint
    assert "python -m scripts.generate_checkout_charts" in entrypoint
    assert "exec uvicorn app.main:app" in entrypoint
    assert entrypoint.index("python -m scripts.checkout_analysis") < entrypoint.index("exec uvicorn app.main:app")
    assert entrypoint.index("python -m scripts.generate_checkout_charts") < entrypoint.index("exec uvicorn app.main:app")
