## Why

The reviewer-facing dashboard and technical report still expose too much internal naming, especially in panel titles, table headers, and numeric labels. Reviewers can see the right data, but they still have to translate field names like `above_normal_rate` and `warning_gap_rate` into business meaning while reading.

This change is needed now because the repository already has the data and decision logic in place; the remaining gap is presentation clarity. Improving the explanation layer makes the existing monitoring workflow easier to evaluate without changing the underlying API contracts.

## What Changes

- Rename Grafana panel titles to reviewer-facing questions and outcomes instead of terse internal labels.
- Replace technical dashboard column headers with explanatory sentence-case copy that makes each number self-describing.
- Keep all dashboard numeric fields raw and sortable while improving their visible units and labels.
- Rewrite the technical report headings and numeric callouts so they explain what each threshold, count, and example means in reviewer language.
- Rewrite visible chart-series labels that currently surface raw snake_case names so trend and forecast visuals stay human-readable.
- Treat "headers" as reviewer-visible copy only: Grafana panel titles, visible Grafana table/chart labels, report section headings, and report numeric callouts/examples.
- Explicitly exclude API JSON field names, Grafana selectors, backend schema names, and environment-variable names from the copy rewrite.
- Update dashboard validation, documentation, and contract references so the renamed reviewer-facing copy remains enforced.
- Preserve the challenge-brief evidence in `database/monitoring-test.md`, including checkout timestamp markers, SQL/chart explanation, and explicit requirement mapping in the report.
- Preserve all existing API payload shapes, dashboard data sources, and anomaly/decision logic.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monitoring-visualization-and-reporting`: tighten reviewer-facing dashboard and report requirements so panel titles, table headers, and numeric presentation explain the underlying monitoring meaning directly.
- `checkout-anomaly-analysis`: tighten the checkout-analysis reporting requirements so friendlier wording does not remove the explicit anomaly evidence required by the challenge brief.

## Impact

- Affected assets: `grafana/dashboard.template.json`, rendered `grafana/dashboard.json`, `report/technical_report.md`, reviewer-facing documentation, and dashboard contract/smoke checks.
- Affected validation: dashboard title/column assertions in tests and Playwright checks.
- Affected specifications: `monitoring-visualization-and-reporting` and `checkout-anomaly-analysis`.
- APIs and response schemas remain unchanged.
- Grafana query selectors, typed columns, API field names, and environment/config names remain unchanged.
