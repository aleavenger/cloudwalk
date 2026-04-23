## Context

CloudWalk already computes the right decision, forecast, and business-impact data for reviewers. The remaining friction is presentation: the dashboard still uses several internal-style panel titles and column labels, and the technical report often lists thresholds and example numbers without explaining their operational meaning in plain reviewer language.

This change is cross-cutting even though it is presentation-focused. It touches the Grafana dashboard template and rendered asset, the technical report, dashboard contract tests, Playwright title checks, and reviewer-facing documentation that names or explains those surfaces. The repository also has an existing contract boundary that must stay intact: API responses remain machine-readable, while the dashboard and report carry the explanatory layer.

The reviewer-visible report is also part of the challenge deliverable described in `database/monitoring-test.md`. That brief requires explicit checkout conclusions, SQL/chart explanation, a real-time monitoring graphic, an anomaly model, automatic reporting, and a document explaining how the challenge was executed. The copy rewrite cannot weaken any of that evidence.

Constraints:
- keep `/metrics`, `/alerts`, `/decision`, `/decision/focus`, and `/decision/forecast/focus` unchanged
- keep Grafana query URLs, parser settings, panel IDs, typed columns, and units compatible with current contract checks
- continue treating `grafana/dashboard.template.json` as the source of truth and `grafana/dashboard.json` as a rendered artifact
- update `SYSTEM_MAP.md`, `INVARIANTS.md`, and `README.md` alongside reviewer-visible behavior changes
- treat "headers" as visible presentation copy only: Grafana panel titles, visible Grafana field labels, report headings, and report numeric callouts/examples
- do not rename API JSON fields, Grafana selectors, backend schema/type names, or environment-variable names

## Goals / Non-Goals

**Goals:**
- make every reviewer-visible dashboard title explain what the panel answers
- replace internal-looking dashboard column headers with explanatory sentence-case copy
- replace raw snake_case chart-series labels with human-readable reviewer-facing names
- make numeric values easier to interpret by clarifying units and meanings without breaking sorting or machine consumption
- rewrite technical-report headings and numeric callouts so thresholds, counts, and anomaly examples explain what they mean
- preserve explicit challenge-brief evidence from `database/monitoring-test.md` while improving readability
- keep validation and documentation aligned with the new reviewer-facing wording

**Non-Goals:**
- changing anomaly thresholds, scoring, forecast behavior, or business-impact calculations
- adding new backend display-string fields or altering API response schemas
- redesigning the dashboard layout, data sources, or panel query structure
- changing reviewer bootstrap flow, authentication behavior, or alert semantics
- renaming API JSON keys, Grafana selectors, backend schema symbols, or environment/config variable names
- weakening or removing the explicit checkout and monitoring evidence the challenge brief asks the reviewer to evaluate

## Decisions

### 1. Keep the change presentation-only

The implementation will not add or rename backend fields. Reviewer-facing explanation will live in Grafana titles, visible column labels, units, markdown copy, and report prose.

Locked scope of "headers and numbers":
- included: Grafana panel titles, visible Grafana field labels, visible chart-series labels, report section headings, report numeric callouts, and report anomaly examples
- excluded: API JSON field names, Grafana selectors, typed-column selectors, backend schema/type names, and environment/config variable names

Why this approach:
- the existing API contract already exposes the required raw numeric fields
- keeping numbers numeric preserves table sorting, typed columns, and downstream compatibility
- the repository already documents that human formatting belongs in Grafana and reviewer-facing materials

Alternative considered:
- add backend-generated display strings such as `2.3 pp above baseline`
- rejected because it would duplicate data, expand the API surface, and blur the machine-readable contract

### 2. Lock the reviewer-facing dashboard copy in the template and tests

The source of truth will remain `grafana/dashboard.template.json`. The change will rename panel titles and visible column labels there, then regenerate `grafana/dashboard.json` through the existing dashboard render path so the provisioned asset matches the template.

Exact panel-title direction:
- `Decision Snapshot` -> `What Needs Attention Right Now`
- `Priority Queue` -> `Why Each Metric Is Ranked This Way`
- `Forecast Risk` -> `What Could Get Worse In The Forecast Window`
- `Recent Evidence` -> `Evidence Behind The Current Recommendation`
- `Business Impact` -> `What This Top Issue Means For The Business`
- `Recent Formal Alerts` -> `Formal Alerts That Have Already Fired`
- `Risk Trend by Metric` -> `How Risk Rates Are Moving Over Time`
- `Transaction Volume Context` -> `How Much Traffic These Rates Represent`
- `Reviewer First Login` -> `How To Read This Dashboard On First Login`

The tests and smoke checks will be updated to assert the new reviewer-facing titles so the copy does not regress silently.

Locked panel-title mapping (must be implemented exactly):
- `Decision Snapshot` -> `What Needs Attention Right Now`
- `Priority Queue` -> `Why Each Metric Is Ranked This Way`
- `Forecast Risk` -> `What Could Get Worse In The Forecast Window`
- `Recent Evidence` -> `Evidence Behind The Current Recommendation`
- `Business Impact` -> `What This Top Issue Means For The Business`
- `Recent Formal Alerts` -> `Formal Alerts That Have Already Fired`
- `Risk Trend by Metric` -> `How Risk Rates Are Moving Over Time`
- `Transaction Volume Context` -> `How Much Traffic These Rates Represent`
- `Reviewer First Login` -> `How To Read This Dashboard On First Login`

Alternative considered:
- update only the rendered `grafana/dashboard.json`
- rejected because the application regenerates that file from the template and would overwrite manual edits

### 3. Narrate numbers through headers and units, not stringified cells

Dashboard table columns will keep their selectors and types but use explanatory display labels. Rates and confidence stay numeric with percent-based rendering; above-normal and warning-gap fields stay numeric and are labeled as percentage-point deltas; counts remain whole-number approximations.

Locked numeric-narration rule:
- keep API numeric fields raw and machine-readable
- keep Grafana column types numeric/timestamp/string as they are today
- do not add backend display-string fields
- do not replace numeric table cells with sentence-style strings

Locked dashboard header mapping (must be implemented exactly for visible `text` labels):
- `generated_at` -> `Decision generated at`
- `overall_status` -> `Overall status right now`
- `top_recommendation` -> `What the reviewer should do next`
- `summary` -> `Why this issue is ranked first`
- `problem_explanation` -> `What is above normal and why it matters`
- `forecast_explanation` -> `What may happen next`
- `metric` -> `Metric under review`
- `decision_status` -> `Action level now`
- `current_severity` -> `Formal alert severity now`
- `risk_score` -> `Priority score (0-100)`
- `confidence` -> `Confidence in this ranking (%)`
- `current_rate` -> `Current rate now (%)`
- `baseline_rate` -> `Typical baseline rate (%)`
- `forecast_rate` -> `Forecast rate within horizon (%)`
- `denied_rate` (trend/forecast charts) -> `Denied rate (%)`
- `failed_rate` (trend/forecast charts) -> `Failed rate (%)`
- `reversed_rate` (trend/forecast charts) -> `Reversed rate (%)`
- `above_normal_rate` -> `Above baseline now (percentage points)`
- `forecast_above_normal_rate` -> `Above baseline within forecast horizon (percentage points)`
- `warning_gap_rate` -> `Gap before formal warning (percentage points remaining)`
- `excess_transactions_now` -> `Extra affected transactions now (approx.)`
- `projected_excess_transactions_horizon` -> `Extra affected transactions within forecast horizon (approx.)`
- `domain_label` -> `Business area affected`
- `likely_owner` -> `Team likely to act`
- `top_auth_codes_display` -> `Top authorization-code clues`
- `recommended_action` -> `Recommended next step`
- `timestamp` (evidence/alerts tables) -> `Recorded at`
- `source` -> `Evidence source`
- `message` -> `What this evidence says`
- `auth_code_top_display` -> `Supporting authorization-code context`
- `top_metric` -> `Top metric driving the issue`
- `severity` -> `Formal alert severity`
- `notification_status` -> `Formal alert handling result`
- `reason` -> `Why the formal alert fired`
- `horizon_label` -> `Forecast horizon`
- `Time` (trend/volume charts) -> `Time`
- `total` -> `Transactions in this time bucket`

Non-visible helper fields such as hidden chart helpers may remain internal because they are not reviewer-facing labels.

Alternative considered:
- use verbose sentence-style strings in each cell
- rejected because it would make tables harder to scan and would destroy numeric sorting behavior

### 4. Keep the report language aligned with the dashboard language

`report/technical_report.md` will adopt explanatory headings and rewrite numeric bullets so each threshold or example states what the number means. This keeps the written narrative consistent with the dashboard’s reviewer-first wording.

Implementation direction:
- heading rewrites will favor question/meaning-driven titles
- threshold bullets will explain the gate or rule instead of only listing a value
- anomaly examples will spell out what happened in the minute window and why it mattered
- the checkout-analysis section must keep the explicit `08h`, `09h`, and `10h`/`12h`/`15h`/`17h` evidence already used for challenge acceptance
- the challenge-requirement mapping section must keep explicit references to the required monitoring endpoint, query/graphic, anomaly model, and automatic reporting deliverables from `database/monitoring-test.md`

Alternative considered:
- update only the dashboard
- rejected because the report is also reviewer-facing and currently repeats the same shorthand problem

### 5. Sync docs and invariants with the presentation contract

`README.md`, `docs/monitoring-methodology.md`, `SYSTEM_MAP.md`, and `INVARIANTS.md` will be updated to reflect the renamed dashboard panels and to restate that the API remains raw numeric while the explanation layer lives in Grafana/reporting.

This keeps the repository’s documented contract aligned with the implemented reviewer experience and avoids drift in future changes.

## Risks / Trade-offs

- [Copy becomes too verbose and hurts scanability] -> Mitigation: keep titles short, keep column labels explanatory but compact, and avoid sentence-length table headers.
- [Dashboard validation becomes brittle because strings are now explicit] -> Mitigation: update the contract and Playwright checks in the same change and keep the locked wording centralized in the template/tests.
- [Reviewers may assume the API changed because labels are friendlier] -> Mitigation: document explicitly that only the presentation layer changed and that raw numeric fields remain unchanged.
- [Report and dashboard wording could drift over time] -> Mitigation: update both surfaces in the same change and reflect the reviewer-facing contract in the spec/docs.

## Migration Plan

1. Update the dashboard template titles, column labels, and any supporting markdown copy.
2. Regenerate the rendered dashboard asset through the existing application render path.
3. Rewrite the technical report headings and numeric callouts to the same reviewer-facing style.
4. Update dashboard tests, smoke checks, and Playwright title assertions to the new wording, while confirming selectors, field types, API field names, and chart-series labels remain unchanged except for visible copy.
5. Update report assertions so the rewritten report still preserves the checkout evidence markers and challenge requirement mapping expected by `database/monitoring-test.md`.
6. Update repository docs and invariants to describe the explanation-layer contract.
7. Execute explicit validation commands:
   - `pytest tests/test_api.py -k 'dashboard or report'`
   - `python3 scripts/check_grafana_dashboard_contract.py`
   - `./scripts/check_grafana_dashboard_playwright.sh` (when Playwright/Chromium is available in the environment)

Rollback is low risk because the change is presentation-only. Reverting the updated copy assets, tests, and docs restores the prior reviewer experience without affecting runtime APIs or decision logic.

## Open Questions

None. The change will proceed as a dashboard/report explanation pass with no backend contract expansion.
