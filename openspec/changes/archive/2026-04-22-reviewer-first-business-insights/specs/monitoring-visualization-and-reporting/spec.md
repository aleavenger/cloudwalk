## MODIFIED Requirements

### Requirement: Submission SHALL provide Grafana-ready monitoring views
The repository SHALL include dashboard assets and supporting data contracts that allow a reviewer to visualize transaction health, operator priorities, predictive risk, business impact, and recent formal alert activity in Grafana.

The implementation SHALL assume:
- datasource plugin: `yesoreyeram-infinity-datasource`
- manual-path datasource target: `http://127.0.0.1:8000`
- one-click-path datasource target: `http://api:8000`
- metrics datasource path: `GET /metrics` using `rows[*]`
- alert datasource path: `GET /alerts` using `alerts[*]`
- decision datasource path: `GET /decision`
- time field name for dashboard panels: `timestamp`

#### Scenario: Dashboard includes reviewer-first business-impact panels
- **WHEN** the Grafana dashboard is imported and connected to the local monitoring service
- **THEN** it SHALL present panels for overall monitoring status, top recommendation, business impact, priority-ranked risks, forecast risk, recent formal alerts, transaction volume context, and reviewer-facing first-login guidance

#### Scenario: Dashboard supports anomaly drilldown with above-normal context
- **WHEN** an anomalous or elevated-risk window is viewed in the monitoring workflow
- **THEN** the visualization layer SHALL provide enough context to inspect current rate, baseline delta, excess affected transactions, threshold proximity, recent evidence, and relevant authorization-code clues rather than only showing aggregate totals

#### Scenario: Dashboard distinguishes predictive guidance from formal alerts
- **WHEN** the dashboard shows both forecasted risk and current alerts
- **THEN** it SHALL make clear which states are predictive/watch guidance and which states represent formal alert history

#### Scenario: Dashboard uses human-readable percentage formatting
- **WHEN** Grafana renders decision and priority fields from the API
- **THEN** it SHALL present confidence and rate values in reviewer-friendly percentage formats without requiring the API contract to replace raw numeric fields with strings

### Requirement: Submission SHALL include reviewer-facing documentation
The repository SHALL include a technical report and startup instructions that explain the problem, the implemented solution, how to run it, and the main findings from the provided datasets.

#### Scenario: Documentation explains reviewer-preferred provider behavior
- **WHEN** the reviewer follows the primary bootstrap flow
- **THEN** the README and first-login guidance SHALL explain that external AI is the preferred reviewer path for richer narrative output while local mode remains a safe deterministic fallback

#### Scenario: Technical report explains business-impact interpretation
- **WHEN** the reviewer reads the report
- **THEN** it SHALL explain how above-normal deltas, excess affected transactions, and likely owner mappings are derived from the monitoring data
