## 1. Dashboard Copy And Presentation

- [x] 1.1 Update `grafana/dashboard.template.json` so every panel title uses reviewer-facing explanatory copy while preserving existing panel IDs, datasource URLs, selectors, parser settings, and field types.
- [x] 1.2 Replace dashboard table and chart labels using the exact locked mapping in the design/spec so all visible decision, business-impact, evidence, alert, forecast, trend, and traffic labels are covered without changing selectors or numeric field types.
- [x] 1.3 Keep narrated-number presentation in Grafana by preserving numeric units/formatting for rates, percentage-point deltas, and count fields, then regenerate `grafana/dashboard.json` from the template-backed render flow.
- [x] 1.4 Keep the copy pass limited to visible presentation labels only; do not rename API JSON keys, Grafana selectors, backend schema/type names, or environment/config variable names.

## 2. Report And Documentation Alignment

- [x] 2.1 Rewrite `report/technical_report.md` headings so each section states what it explains in reviewer language rather than terse internal shorthand.
- [x] 2.2 Rewrite report numeric callouts, thresholds, and anomaly examples so each number explains its operational meaning and unit/window context while preserving the explicit checkout evidence markers required by the challenge brief.
- [x] 2.3 Update `README.md`, `docs/monitoring-methodology.md`, `SYSTEM_MAP.md`, and `INVARIANTS.md` to reflect the renamed dashboard panels and to state that the API remains raw numeric while the dashboard/report provide the explanatory layer.
- [x] 2.4 Keep the report's challenge mapping explicit: the rewritten document must still state which runtime artifact satisfies the required monitoring endpoint, query/graphic, anomaly model, and automatic reporting items from `database/monitoring-test.md`.

## 3. Contract And Reviewer Validation

- [x] 3.1 Update dashboard contract assertions in `tests/test_api.py` and `scripts/check_grafana_dashboard_contract.py` to the new panel titles and visible column labels while keeping existing structural assertions intact.
- [x] 3.2 Extend or update automated report assertions so the rewritten report still proves challenge-brief compliance, including checkout evidence markers and explicit challenge requirement mapping.
- [x] 3.3 Update `scripts/check_grafana_dashboard_playwright.js` so the reviewer-visible smoke check looks for the new explanatory panel titles.
- [x] 3.4 Run `pytest tests/test_api.py -k 'dashboard or report'` and confirm dashboard/report contract assertions pass.
- [x] 3.5 Run `python3 scripts/check_grafana_dashboard_contract.py` and confirm the dashboard provisioning contract passes with new titles/labels.
- [x] 3.6 Run `./scripts/check_grafana_dashboard_playwright.sh` when Playwright/Chromium is available and confirm reviewer-visible dashboard title checks pass.
