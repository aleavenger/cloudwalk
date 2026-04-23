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
    assert dashboard.get("time") == {"from": "2025-07-12T13:45:00Z", "to": "2025-07-15T14:14:00Z"}

    panel_titles = {panel.get("title") for panel in dashboard.get("panels", [])}
    assert "What Needs Attention Right Now" in panel_titles
    assert "Why Each Metric Is Ranked This Way" in panel_titles
    assert "What Could Get Worse In The Forecast Window" in panel_titles
    assert "Evidence Behind The Current Recommendation" in panel_titles
    assert "Formal Alerts That Have Already Fired" in panel_titles
    assert "What This Top Issue Means For The Business" in panel_titles
    assert "How Risk Rates Are Moving Over Time" in panel_titles
    assert "How Much Traffic These Rates Represent" in panel_titles
    assert "How To Read This Dashboard On First Login" in panel_titles

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
    _assert_column(panel2.get("columns", []), "Priority score (0-100)", "number")
    _assert_column(panel2.get("columns", []), "Confidence in this ranking (%)", "number")
    _assert_column(panel2.get("columns", []), "Current rate now (%)", "number")
    _assert_column(panel2.get("columns", []), "Typical baseline rate (%)", "number")
    _assert_column(panel2.get("columns", []), "Forecast rate within horizon (%)", "number")
    _assert_column(panel2.get("columns", []), "Top authorization-code clues", "string")
    _assert_column(panel2.get("columns", []), "Above baseline now (percentage points)", "number")
    _assert_column(panel2.get("columns", []), "Above baseline within forecast horizon (percentage points)", "number")
    _assert_column(panel2.get("columns", []), "Gap before formal warning (percentage points remaining)", "number")
    _assert_column(panel2.get("columns", []), "Extra affected transactions now (approx.)", "number")
    _assert_column(panel2.get("columns", []), "Extra affected transactions within forecast horizon (approx.)", "number")
    _assert_column(panel2.get("columns", []), "Business area affected", "string")
    _assert_column(panel2.get("columns", []), "Team likely to act", "string")
    _assert_column(panel2.get("columns", []), "Recommended next step", "string")
    panel2_full = next(p for p in dashboard.get("panels", []) if p.get("id") == 2)
    _assert_percent_override(panel2_full, "Confidence in this ranking (%)")
    _assert_percent_override(panel2_full, "Current rate now (%)")
    _assert_percent_override(panel2_full, "Typical baseline rate (%)")
    _assert_percent_override(panel2_full, "Forecast rate within horizon (%)")
    _assert_percent_override(panel2_full, "Above baseline now (percentage points)")
    _assert_percent_override(panel2_full, "Above baseline within forecast horizon (percentage points)")
    _assert_percent_override(panel2_full, "Gap before formal warning (percentage points remaining)")

    panel4 = _target_by_panel_id(dashboard, 4)
    assert panel4.get("format") == "table"
    assert panel4.get("parser") == "backend"
    assert panel4.get("url") == "http://api:8000/decision/focus"
    _assert_column(panel4.get("columns", []), "Recorded at", "timestamp")
    _assert_column(panel4.get("columns", []), "Evidence source", "string")
    _assert_column(panel4.get("columns", []), "What this evidence says", "string")
    _assert_column(panel4.get("columns", []), "Supporting authorization-code context", "string")

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
    _assert_column(panel9.get("columns", []), "Top metric driving the issue", "string")
    _assert_column(panel9.get("columns", []), "Business area affected", "string")
    _assert_column(panel9.get("columns", []), "Team likely to act", "string")
    _assert_column(panel9.get("columns", []), "Above baseline now (percentage points)", "number")
    _assert_column(panel9.get("columns", []), "Gap before formal warning (percentage points remaining)", "number")
    _assert_column(panel9.get("columns", []), "Extra affected transactions now (approx.)", "number")
    _assert_column(panel9.get("columns", []), "Extra affected transactions within forecast horizon (approx.)", "number")
    panel9_full = next(p for p in dashboard.get("panels", []) if p.get("id") == 9)
    _assert_percent_override(panel9_full, "Above baseline now (percentage points)")
    _assert_percent_override(panel9_full, "Gap before formal warning (percentage points remaining)")


if __name__ == "__main__":
    main()
