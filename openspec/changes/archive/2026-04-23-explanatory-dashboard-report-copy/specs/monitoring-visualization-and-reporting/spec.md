## MODIFIED Requirements

### Requirement: Submission SHALL provide Grafana-ready monitoring views
The repository SHALL include dashboard assets and supporting data contracts that allow a reviewer to visualize transaction health, operator priorities, predictive risk, business impact, and recent formal alert activity in Grafana without having to translate internal field names into reviewer-facing meaning.

The implementation SHALL assume:
- datasource plugin: `yesoreyeram-infinity-datasource`
- manual-path datasource target: `http://127.0.0.1:8000`
- one-click-path datasource target: `http://api:8000`
- metrics datasource path: `GET /metrics` using `rows[*]`
- alert datasource path: `GET /alerts` using `alerts[*]`
- decision datasource path: `GET /decision`
- time field name for dashboard panels: `timestamp`
- pinned plugin version documented in README and Grafana setup notes

#### Scenario: Dashboard includes reviewer-first business-impact panels
- **WHEN** the Grafana dashboard is imported and connected to the local monitoring service
- **THEN** it SHALL present panels for overall monitoring status, top recommendation, business impact, priority-ranked risks, forecast risk, recent formal alerts, transaction volume context, and reviewer-facing first-login guidance
- **AND** those panels SHALL use reviewer-facing titles that directly describe what the reviewer is learning from each panel rather than terse internal shorthand

#### Scenario: Dashboard supports anomaly drilldown with above-normal context
- **WHEN** an anomalous or elevated-risk window is viewed in the monitoring workflow
- **THEN** the visualization layer SHALL provide enough context to inspect current rate, baseline delta, excess affected transactions, threshold proximity, recent evidence, and relevant authorization-code clues rather than only showing aggregate totals

#### Scenario: Dashboard labels explain metric meaning directly
- **WHEN** Grafana renders decision, business-impact, evidence, and alert tables
- **THEN** visible panel titles and column headers SHALL explain the reviewer-facing meaning of the data instead of exposing raw internal field names such as `above_normal_rate`, `warning_gap_rate`, or `top_metric` as the primary label text

#### Scenario: Dashboard title and header mapping is implemented as an exact contract
- **WHEN** the reviewer-facing copy update is implemented for the provisioned dashboard
- **THEN** panel titles SHALL match this exact mapping:
- `Decision Snapshot` -> `What Needs Attention Right Now`
- `Priority Queue` -> `Why Each Metric Is Ranked This Way`
- `Forecast Risk` -> `What Could Get Worse In The Forecast Window`
- `Recent Evidence` -> `Evidence Behind The Current Recommendation`
- `Business Impact` -> `What This Top Issue Means For The Business`
- `Recent Formal Alerts` -> `Formal Alerts That Have Already Fired`
- `Risk Trend by Metric` -> `How Risk Rates Are Moving Over Time`
- `Transaction Volume Context` -> `How Much Traffic These Rates Represent`
- `Reviewer First Login` -> `How To Read This Dashboard On First Login`
- **AND** visible table-column labels SHALL match this exact mapping:
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

#### Scenario: Only visible presentation labels change
- **WHEN** the explanatory dashboard/report copy change is implemented
- **THEN** the scope of "headers" SHALL be limited to Grafana panel titles, visible Grafana field labels, visible chart-series labels, report section headings, and report numeric callouts/examples
- **AND** the change SHALL NOT rename API JSON field names, Grafana selectors, backend schema/type names, or environment/config variable names

#### Scenario: Numeric narration remains presentation-only
- **WHEN** reviewer-facing numeric explanation is added to the dashboard and report
- **THEN** API numeric fields SHALL remain raw and machine-readable
- **AND** Grafana SHALL keep the existing typed field configuration for those values instead of replacing numeric cells with sentence-style strings
- **AND** the implementation SHALL NOT introduce backend-generated display-string fields for those numeric values

#### Scenario: Dashboard distinguishes predictive guidance from formal alerts
- **WHEN** the dashboard shows both forecasted risk and current alerts
- **THEN** it SHALL make clear which states are predictive/watch guidance and which states represent formal alert history

#### Scenario: Dashboard uses narrated numeric formatting while preserving raw values
- **WHEN** Grafana renders decision and priority fields from the API
- **THEN** it SHALL present confidence and rate values in reviewer-friendly percentage formats
- **AND** it SHALL label above-normal and warning-gap fields as percentage-point-style deltas and count fields as approximate whole-number impact values
- **AND** it SHALL do so without requiring the API contract to replace raw numeric fields with strings

#### Scenario: Chart legends avoid raw snake_case labels
- **WHEN** the reviewer reads the forecast-risk and risk-trend charts
- **THEN** visible chart-series labels SHALL use reviewer-facing names instead of raw field names such as `denied_rate`, `failed_rate`, or `reversed_rate`

#### Scenario: Dashboard explains first-login reviewer details
- **WHEN** the reviewer opens the provisioned dashboard for the first time
- **THEN** the dashboard SHALL surface a clear note covering Grafana credentials, API-key usage, selected provider mode, and the difference between predictive guidance and formal alerts

#### Scenario: Dashboard import is reproducible from documentation
- **WHEN** a reviewer follows the README setup instructions
- **THEN** the reviewer SHALL be able to install the required Grafana plugin, configure the datasource, import the dashboard JSON, and render data without editing application code

#### Scenario: Dashboard setup uses pinned plugin version
- **WHEN** a reviewer follows the Grafana setup instructions
- **THEN** the instructions SHALL specify an exact plugin version rather than an unbounded latest install

#### Scenario: One-click mode provisions datasource automatically
- **WHEN** a reviewer starts the Docker Compose reviewer stack
- **THEN** Grafana SHALL have the API datasource preconfigured without requiring manual UI setup

#### Scenario: One-click mode imports dashboard automatically
- **WHEN** a reviewer starts the Docker Compose reviewer stack
- **THEN** the Grafana dashboard SHALL be available without a manual import step

#### Scenario: One-click mode targets the internal API service URL
- **WHEN** the provisioned Grafana datasource is created for Docker Compose mode
- **THEN** it SHALL query the API through the internal Compose service URL rather than `127.0.0.1`

### Requirement: Submission SHALL include reviewer-facing documentation
The repository SHALL include a technical report and startup instructions that explain the problem, the implemented solution, how to run it, and the main findings from the provided datasets in reviewer-facing language that does not require the reader to decode internal shorthand.

#### Scenario: Reviewer can start the project from repository documentation
- **WHEN** a reviewer opens the repository without prior context
- **THEN** the README SHALL provide the commands needed to install dependencies, run the monitoring service, and load the dashboard artifacts

#### Scenario: Technical report explains methods and limitations
- **WHEN** the reviewer reads the report
- **THEN** it SHALL document the anomaly methodology, the alerting approach, the decision-guidance approach, the automatic team-notification approach, and the known limitations of the local implementation

#### Scenario: Technical report headings and numeric callouts explain meaning directly
- **WHEN** the reviewer reads the technical report
- **THEN** section headings SHALL describe what each section explains in reviewer language rather than relying on terse internal headings alone
- **AND** numeric thresholds, counts, and anomaly examples SHALL explain what each value means operationally instead of appearing only as shorthand bullets

#### Scenario: Report maps implementation back to prompt requirements
- **WHEN** the reviewer checks the repository against `database/monitoring-test.md`
- **THEN** the technical report SHALL explain which runtime artifact satisfies the required monitoring endpoint, real-time visualization, anomaly model, and automatic anomaly reporting responsibilities

#### Scenario: Docker Compose is the primary reviewer path
- **WHEN** the reviewer follows the README startup instructions
- **THEN** the README SHALL present the Docker Compose flow as the primary setup path and the manual local flow only as a fallback

#### Scenario: README documents demo-only credentials
- **WHEN** the reviewer reads the Docker Compose startup instructions
- **THEN** the README SHALL list the default Grafana admin credentials and the local demo API-key behavior explicitly

#### Scenario: Documentation explains decision provider behavior
- **WHEN** the reviewer configures local or external decision guidance
- **THEN** the documentation SHALL explain the default local mode, optional external mode, and fallback behavior when the external provider is unavailable

#### Scenario: Documentation explains reviewer-preferred provider behavior
- **WHEN** the reviewer follows the primary bootstrap flow
- **THEN** the README and first-login guidance SHALL explain that external AI is the preferred reviewer path for richer narrative output while local mode remains a safe deterministic fallback

#### Scenario: Technical report explains business-impact interpretation
- **WHEN** the reviewer reads the report
- **THEN** it SHALL explain how above-normal deltas, excess affected transactions, and likely owner mappings are derived from the monitoring data

#### Scenario: Documentation distinguishes presentation explanation from API contract
- **WHEN** the reviewer reads the README, methodology notes, or technical report
- **THEN** those documents SHALL explain that reviewer-facing dashboard/report wording is more descriptive while the underlying API fields remain raw numeric and machine-readable

#### Scenario: Documentation distinguishes aggregate and event ingestion paths
- **WHEN** a reviewer reads the monitoring API documentation
- **THEN** the repository SHALL explain that `POST /monitor` is the aggregate window replay endpoint and `POST /monitor/transaction` is the additive single-event ingestion endpoint

#### Scenario: Documentation matches runtime provisioning behavior
- **WHEN** the reviewer follows the README and report setup notes
- **THEN** those documents SHALL describe the compose-provisioned Grafana plugin/runtime and SHALL NOT require manual steps that the one-click stack already performs automatically
