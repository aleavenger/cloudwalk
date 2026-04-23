## MODIFIED Requirements

### Requirement: Submission SHALL include reviewer-facing documentation
The repository SHALL include a technical report and startup instructions that explain the problem, the implemented solution, how to run it, and the main findings from the provided datasets.

#### Scenario: Reviewer can start the project from repository documentation
- **WHEN** a reviewer opens the repository without prior context
- **THEN** the README SHALL provide the commands needed to install dependencies, run the monitoring service, and load the dashboard artifacts

#### Scenario: Technical report explains methods and limitations
- **WHEN** the reviewer reads the report
- **THEN** it SHALL document the anomaly methodology, the alerting approach, the decision-guidance approach, the automatic team-notification approach, and the known limitations of the local implementation

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

#### Scenario: Documentation distinguishes aggregate and event ingestion paths
- **WHEN** a reviewer reads the monitoring API documentation
- **THEN** the repository SHALL explain that `POST /monitor` is the aggregate window replay endpoint and `POST /monitor/transaction` is the additive single-event ingestion endpoint

#### Scenario: Documentation matches runtime provisioning behavior
- **WHEN** the reviewer follows the README and report setup notes
- **THEN** those documents SHALL describe the compose-provisioned Grafana plugin/runtime and SHALL NOT require manual steps that the one-click stack already performs automatically
