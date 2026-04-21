## Purpose

Define dashboard, reporting, and reviewer-facing deliverables so anomaly insights are observable, reproducible, and easy to evaluate.

## Requirements

### Requirement: Submission SHALL provide Grafana-ready monitoring views
The repository SHALL include dashboard assets and supporting data contracts that allow a reviewer to visualize transaction health, alertable metrics, and recent alert activity in Grafana.

The implementation SHALL assume:
- datasource plugin: `yesoreyeram-infinity-datasource`
- manual-path datasource target: `http://127.0.0.1:8000`
- one-click-path datasource target: `http://api:8000`
- metrics datasource path: `GET /metrics` using `rows[*]`
- alert datasource path: `GET /alerts` using `alerts[*]`
- time field name for dashboard panels: `timestamp`
- pinned plugin version documented in README and Grafana setup notes

#### Scenario: Dashboard includes core monitoring panels
- **WHEN** the Grafana dashboard is imported and connected to the local monitoring service
- **THEN** it SHALL present panels for transaction volume, denied rate, failed rate, reversed rate, active alert state, and recent alerts

#### Scenario: Dashboard supports anomaly drilldown
- **WHEN** an anomalous window is viewed in the monitoring workflow
- **THEN** the visualization layer SHALL provide enough context to inspect the relevant window rather than only showing aggregate daily totals

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

### Requirement: Authorization code data SHALL enrich anomaly explanation
The submission SHALL use `transactions_auth_codes.csv` to help explain anomalous transaction windows and highlight the dominant codes associated with those windows.

#### Scenario: Alert review includes auth-code mix
- **WHEN** an alertable anomalous window is reviewed
- **THEN** the submission SHALL expose the leading authorization codes for that window or period alongside the status-based alert context

#### Scenario: Report uses auth codes for triage context
- **WHEN** the technical report explains notable anomalies
- **THEN** it SHALL describe whether the anomaly appears concentrated in a small number of authorization codes or spread across multiple codes

### Requirement: Submission SHALL include reviewer-facing documentation
The repository SHALL include a technical report and startup instructions that explain the problem, the implemented solution, how to run it, and the main findings from the provided datasets.

#### Scenario: Reviewer can start the project from repository documentation
- **WHEN** a reviewer opens the repository without prior context
- **THEN** the README SHALL provide the commands needed to install dependencies, run the monitoring service, and load the dashboard artifacts

#### Scenario: Technical report explains methods and limitations
- **WHEN** the reviewer reads the report
- **THEN** it SHALL document the anomaly methodology, the main dataset findings, the alerting approach, and the known limitations of the local implementation

#### Scenario: Docker Compose is the primary reviewer path
- **WHEN** the reviewer follows the README startup instructions
- **THEN** the README SHALL present the Docker Compose flow as the primary setup path and the manual local flow only as a fallback

#### Scenario: README documents demo-only credentials
- **WHEN** the reviewer reads the Docker Compose startup instructions
- **THEN** the README SHALL list the default Grafana admin credentials and the local demo API-key behavior explicitly
