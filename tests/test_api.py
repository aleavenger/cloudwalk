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


def test_health_is_public():
    client = TestClient(create_app(_settings(api_key="secret")))
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_protected_endpoints_require_api_key():
    client = TestClient(create_app(_settings(api_key="secret")))
    assert client.get("/metrics").status_code == 401
    assert client.get("/alerts").status_code == 401
    assert client.post("/monitor", json=_payload("2025-07-12 14:00:00")).status_code == 401


def test_valid_api_key_allows_access():
    client = TestClient(create_app(_settings(api_key="secret")))
    headers = {"X-API-Key": "secret"}
    assert client.get("/metrics", headers=headers).status_code == 200
    assert client.get("/alerts", headers=headers).status_code == 200


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
    denied_spike = client.post("/monitor", json=_payload("2025-07-12 17:18:00", approved=100, denied=54, failed=1, reversed=1, backend_reversed=1, refunded=1))
    assert denied_spike.status_code == 200
    assert denied_spike.json()["recommendation"] == "alert"
    assert "denied" in denied_spike.json()["triggered_metrics"]

    failed_spike = client.post("/monitor", json=_payload("2025-07-15 04:30:00", approved=80, denied=4, failed=10, reversed=1, backend_reversed=1, refunded=1))
    assert failed_spike.status_code == 200
    assert failed_spike.json()["recommendation"] == "alert"
    assert "failed" in failed_spike.json()["triggered_metrics"]

    reversed_spike = client.post("/monitor", json=_payload("2025-07-14 06:33:00", approved=90, denied=4, failed=1, reversed=7, backend_reversed=1, refunded=1))
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
    resp = client.post("/monitor", data=large_raw, headers={"content-type": "application/json"})
    assert resp.status_code == 422


def test_metrics_shape():
    client = TestClient(create_app(_settings()))
    resp = client.get("/metrics")
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    assert rows
    first = rows[0]
    for key in ["timestamp", "total", "approved_rate", "denied_rate", "failed_rate", "reversed_rate", "alert_severity"]:
        assert key in first


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
    log_text = __import__("pathlib").Path("logs/alerts.log").read_text(encoding="utf-8")
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
    codes = [item[0] for item in alerts[0]["auth_code_top"]]
    assert "00" in codes


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


def test_dashboard_contains_active_alert_state_panel():
    dashboard = json.loads(Path("grafana/dashboard.json").read_text(encoding="utf-8"))
    titles = {panel.get("title") for panel in dashboard.get("panels", [])}
    assert "Transaction Volume" in titles
    assert "Denied / Failed / Reversed Rates" in titles
    assert "Recent Alerts" in titles
    assert "Active Alert State" in titles


def test_checkout_report_acceptance_markers():
    report = __import__("pathlib").Path("report/technical_report.md").read_text(encoding="utf-8")
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
