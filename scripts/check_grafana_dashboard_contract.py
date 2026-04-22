from __future__ import annotations

import json
from pathlib import Path


def _target_by_panel_id(dashboard: dict, panel_id: int) -> dict:
    panel = next((p for p in dashboard.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise AssertionError(f"missing panel id {panel_id}")
    targets = panel.get("targets", [])
    if not targets:
        raise AssertionError(f"panel {panel_id} has no targets")
    return targets[0]


def _assert_column(columns: list[dict], text: str, col_type: str) -> None:
    for column in columns:
        if column.get("text") == text and column.get("type") == col_type:
            return
    raise AssertionError(f"missing column text={text} type={col_type}")


def main() -> None:
    dashboard = json.loads(Path("grafana/dashboard.json").read_text(encoding="utf-8"))

    panel_titles = {panel.get("title") for panel in dashboard.get("panels", [])}
    assert "Decision Snapshot" in panel_titles
    assert "Priority Queue" in panel_titles
    assert "Forecast Risk" in panel_titles
    assert "Recent Evidence" in panel_titles
    assert "Recent Formal Alerts" in panel_titles
    assert "Risk Trend by Metric" in panel_titles
    assert "Transaction Volume Context" in panel_titles
    assert "Reviewer First Login" in panel_titles

    panel1 = _target_by_panel_id(dashboard, 1)
    assert panel1.get("format") == "table"
    assert panel1.get("parser") == "backend"
    _assert_column(panel1.get("columns", []), "generated_at", "timestamp")
    _assert_column(panel1.get("columns", []), "overall_status", "string")

    panel2 = _target_by_panel_id(dashboard, 2)
    assert panel2.get("format") == "table"
    assert panel2.get("parser") == "backend"
    _assert_column(panel2.get("columns", []), "metric", "string")
    _assert_column(panel2.get("columns", []), "risk_score", "number")
    _assert_column(panel2.get("columns", []), "top_auth_codes_display", "string")

    panel4 = _target_by_panel_id(dashboard, 4)
    assert panel4.get("format") == "table"
    assert panel4.get("parser") == "backend"
    _assert_column(panel4.get("columns", []), "auth_code_top_display", "string")

    panel3 = _target_by_panel_id(dashboard, 3)
    assert panel3.get("format") == "timeseries"
    assert panel3.get("parser") == "backend"
    _assert_column(panel3.get("columns", []), "Time", "timestamp")
    _assert_column(panel3.get("columns", []), "forecast_rate", "number")

    panel6 = _target_by_panel_id(dashboard, 6)
    assert panel6.get("format") == "timeseries"
    assert panel6.get("parser") == "backend"
    _assert_column(panel6.get("columns", []), "Time", "timestamp")
    _assert_column(panel6.get("columns", []), "denied_rate", "number")
    _assert_column(panel6.get("columns", []), "failed_rate", "number")
    _assert_column(panel6.get("columns", []), "reversed_rate", "number")

    panel7 = _target_by_panel_id(dashboard, 7)
    assert panel7.get("format") == "timeseries"
    assert panel7.get("parser") == "backend"
    _assert_column(panel7.get("columns", []), "Time", "timestamp")
    _assert_column(panel7.get("columns", []), "total", "number")


if __name__ == "__main__":
    main()
