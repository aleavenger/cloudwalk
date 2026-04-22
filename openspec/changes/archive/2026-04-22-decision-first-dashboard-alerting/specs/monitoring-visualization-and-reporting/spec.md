## MODIFIED Requirements

### Requirement: Submission SHALL provide Grafana-ready monitoring views
The repository SHALL include dashboard assets and supporting data contracts that allow a reviewer to visualize transaction health, operator priorities, predictive risk, and recent formal alert activity in Grafana.

The implementation SHALL assume:
- datasource plugin: `yesoreyeram-infinity-datasource`
- manual-path datasource target: `http://127.0.0.1:8000`
- one-click-path datasource target: `http://api:8000`
- metrics datasource path: `GET /metrics` using `rows[*]`
- alert datasource path: `GET /alerts` using `alerts[*]`
- decision datasource path: `GET /decision`
- time field name for dashboard panels: `timestamp`
- pinned plugin version documented in README and Grafana setup notes

#### Scenario: Dashboard includes decision-first monitoring panels
- **WHEN** the Grafana dashboard is imported and connected to the local monitoring service
- **THEN** it SHALL present panels for overall monitoring status, top recommendation, priority-ranked risks, forecast risk, recent formal alerts, transaction volume context, and reviewer-facing first-login guidance

#### Scenario: Dashboard supports anomaly drilldown
- **WHEN** an anomalous or elevated-risk window is viewed in the monitoring workflow
- **THEN** the visualization layer SHALL provide enough context to inspect current rate, baseline delta, recent evidence, and relevant authorization-code clues rather than only showing aggregate totals

#### Scenario: Dashboard distinguishes predictive guidance from formal alerts
- **WHEN** the dashboard shows both forecasted risk and current alerts
- **THEN** it SHALL make clear which states are predictive/watch guidance and which states represent formal alert history

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
The repository SHALL include a technical report and startup instructions that explain the problem, the implemented solution, how to run it, and the main findings from the provided datasets.

#### Scenario: Reviewer can start the project from repository documentation
- **WHEN** a reviewer opens the repository without prior context
- **THEN** the README SHALL provide the commands needed to install dependencies, run the monitoring service, and load the dashboard artifacts

#### Scenario: Technical report explains methods and limitations
- **WHEN** the reviewer reads the report
- **THEN** it SHALL document the anomaly methodology, the alerting approach, the decision-guidance approach, and the known limitations of the local implementation

#### Scenario: Docker Compose is the primary reviewer path
- **WHEN** the reviewer follows the README startup instructions
- **THEN** the README SHALL present the Docker Compose flow as the primary setup path and the manual local flow only as a fallback

#### Scenario: README documents demo-only credentials
- **WHEN** the reviewer reads the Docker Compose startup instructions
- **THEN** the README SHALL list the default Grafana admin credentials and the local demo API-key behavior explicitly

#### Scenario: Documentation explains decision provider behavior
- **WHEN** the reviewer configures local or external decision guidance
- **THEN** the documentation SHALL explain the default local mode, optional external mode, and fallback behavior when the external provider is unavailable
