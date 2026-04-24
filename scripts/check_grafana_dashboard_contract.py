from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import create_app


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

def _assert_percent_override(panel: dict, field_name: str) -> None:
    for override in panel.get("fieldConfig", {}).get("overrides", []):
        matcher = override.get("matcher", {})
        if matcher.get("id") != "byName" or matcher.get("options") != field_name:
            continue
        for prop in override.get("properties", []):
            if prop.get("id") == "unit" and prop.get("value") == "percentunit":
                return
    raise AssertionError(f"missing percentunit override for {field_name}")


def main() -> None:
    create_app()
    dashboard = json.loads(Path("grafana/dashboard.json").read_text(encoding="utf-8"))
    assert dashboard.get("refresh") == "30m"
    assert dashboard.get("time") == {"from": "2025-07-12T13:45:00Z", "to": "2025-07-15T14:14:00Z"}

    panel_titles = {panel.get("title") for panel in dashboard.get("panels", [])}
    assert "Current Decision at Latest Minute" in panel_titles
    assert "Metric Ranking Behind Current Decision" in panel_titles
    assert "Forecast from Latest Minute (+5m to +30m)" in panel_titles
    assert "Evidence for Current Decision" in panel_titles
    assert "Runtime Formal Alert Log (This Session)" in panel_titles
    assert "Business Impact of Current Top Metric" in panel_titles
    assert "Historical Hourly Risk Rates (Focus Window)" in panel_titles
    assert "Historical Hourly Volume (Focus Window)" in panel_titles
    assert "How to Read This Page" in panel_titles

    panel1 = _target_by_panel_id(dashboard, 1)
    assert panel1.get("format") == "table"
    assert panel1.get("parser") == "backend"
    assert panel1.get("url") == "http://api:8000/decision/focus"
    _assert_column(panel1.get("columns", []), "Decision generated at", "timestamp")
    _assert_column(panel1.get("columns", []), "Overall status right now", "string")
    _assert_column(panel1.get("columns", []), "What the reviewer should do next", "string")
    _assert_column(panel1.get("columns", []), "Why this issue is ranked first", "string")
    _assert_column(panel1.get("columns", []), "What is above normal and why it matters", "string")
    _assert_column(panel1.get("columns", []), "What may happen next", "string")

    panel2 = _target_by_panel_id(dashboard, 2)
    assert panel2.get("format") == "table"
    assert panel2.get("parser") == "backend"
    assert panel2.get("url") == "http://api:8000/decision/focus"
    _assert_column(panel2.get("columns", []), "Metric under review", "string")
    _assert_column(panel2.get("columns", []), "Action level now", "string")
    _assert_column(panel2.get("columns", []), "Formal alert severity now", "string")
    _assert_column(panel2.get("columns", []), "Current rate now (%)", "number")
    _assert_column(panel2.get("columns", []), "Typical baseline rate (%)", "number")
    _assert_column(panel2.get("columns", []), "Forecast rate within horizon (%)", "number")
    _assert_column(panel2.get("columns", []), "Distance to formal warning threshold", "number")
    _assert_column(panel2.get("columns", []), "Team likely to act", "string")
    _assert_column(panel2.get("columns", []), "Recommended next step", "string")
    _assert_column(panel2.get("columns", []), "Auth-code context at latest minute", "string")
    panel2_full = next(p for p in dashboard.get("panels", []) if p.get("id") == 2)
    _assert_percent_override(panel2_full, "Current rate now (%)")
    _assert_percent_override(panel2_full, "Typical baseline rate (%)")
    _assert_percent_override(panel2_full, "Forecast rate within horizon (%)")
    _assert_percent_override(panel2_full, "Distance to formal warning threshold")

    panel4 = _target_by_panel_id(dashboard, 4)
    assert panel4.get("format") == "table"
    assert panel4.get("parser") == "backend"
    assert panel4.get("url") == "http://api:8000/decision/focus"
    _assert_column(panel4.get("columns", []), "Recorded at", "timestamp")
    _assert_column(panel4.get("columns", []), "Evidence source", "string")
    _assert_column(panel4.get("columns", []), "What this evidence says", "string")
    _assert_column(panel4.get("columns", []), "Auth-code context at latest minute", "string")

    panel3 = _target_by_panel_id(dashboard, 3)
    assert panel3.get("format") == "table"
    assert panel3.get("parser") == "backend"
    assert panel3.get("url") == "http://api:8000/decision/forecast/focus"
    _assert_column(panel3.get("columns", []), "Forecast horizon", "string")
    _assert_column(panel3.get("columns", []), "Denied rate (%)", "number")
    _assert_column(panel3.get("columns", []), "Failed rate (%)", "number")
    _assert_column(panel3.get("columns", []), "Reversed rate (%)", "number")
    panel3_full = next(p for p in dashboard.get("panels", []) if p.get("id") == 3)
    assert panel3_full.get("type") == "barchart"
    assert panel3_full.get("fieldConfig", {}).get("defaults", {}).get("unit") == "percentunit"

    panel5 = _target_by_panel_id(dashboard, 5)
    assert panel5.get("format") == "table"
    assert panel5.get("parser") == "backend"
    assert panel5.get("url") == "http://api:8000/alerts"
    _assert_column(panel5.get("columns", []), "Recorded at", "timestamp")
    _assert_column(panel5.get("columns", []), "Formal alert severity", "string")
    _assert_column(panel5.get("columns", []), "Formal alert handling result", "string")
    _assert_column(panel5.get("columns", []), "Why the formal alert fired", "string")

    panel6 = _target_by_panel_id(dashboard, 6)
    assert panel6.get("format") == "timeseries"
    assert panel6.get("parser") == "backend"
    assert panel6.get("url") == "http://api:8000/metrics/focus?bucket=hour"
    _assert_column(panel6.get("columns", []), "Time", "timestamp")
    _assert_column(panel6.get("columns", []), "Denied rate (%)", "number")
    _assert_column(panel6.get("columns", []), "Failed rate (%)", "number")
    _assert_column(panel6.get("columns", []), "Reversed rate (%)", "number")
    panel6_full = next(p for p in dashboard.get("panels", []) if p.get("id") == 6)
    assert panel6_full.get("fieldConfig", {}).get("defaults", {}).get("unit") == "percentunit"

    panel7 = _target_by_panel_id(dashboard, 7)
    assert panel7.get("format") == "timeseries"
    assert panel7.get("parser") == "backend"
    assert panel7.get("url") == "http://api:8000/metrics/focus?bucket=hour"
    _assert_column(panel7.get("columns", []), "Time", "timestamp")
    _assert_column(panel7.get("columns", []), "Transactions in this time bucket", "number")
    panel7_full = next(p for p in dashboard.get("panels", []) if p.get("id") == 7)
    assert panel7_full.get("fieldConfig", {}).get("defaults", {}).get("custom", {}).get("drawStyle") == "bars"

    panel9 = _target_by_panel_id(dashboard, 9)
    assert panel9.get("format") == "table"
    assert panel9.get("parser") == "backend"
    assert panel9.get("url") == "http://api:8000/decision/focus"
    _assert_column(panel9.get("columns", []), "Metric", "string")
    _assert_column(panel9.get("columns", []), "Business area", "string")
    _assert_column(panel9.get("columns", []), "Team", "string")
    _assert_column(panel9.get("columns", []), "Gap vs normal", "number")
    _assert_column(panel9.get("columns", []), "Gap to warning", "number")
    _assert_column(panel9.get("columns", []), "Excess now", "number")
    _assert_column(panel9.get("columns", []), "Excess in 30m", "number")
    panel9_full = next(p for p in dashboard.get("panels", []) if p.get("id") == 9)
    _assert_percent_override(panel9_full, "Gap vs normal")
    _assert_percent_override(panel9_full, "Gap to warning")

    panel8_full = next(p for p in dashboard.get("panels", []) if p.get("id") == 8)
    panel8_content = panel8_full.get("options", {}).get("content", "")
    assert "Dashboard refresh is fixed at `30m`." in panel8_content
    assert "`Current decision` panels use the latest minute in the focus window." in panel8_content
    assert "`Runtime alert log` shows only alerts generated in this session" in panel8_content
    assert "`external` mode is optional narrative polish;" in panel8_content
    assert "page loads and each refresh cycle can trigger repeated AI-backed narrative requests" in panel8_content


if __name__ == "__main__":
    main()
