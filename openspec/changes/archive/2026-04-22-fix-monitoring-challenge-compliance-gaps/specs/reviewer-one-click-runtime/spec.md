## MODIFIED Requirements

### Requirement: Reviewer stack SHALL start with a single Docker Compose command
The repository SHALL provide a Docker Compose based runtime that allows a reviewer to start the monitoring API, Grafana, and a local mock team-notification receiver through one guided bootstrap entrypoint that invokes Docker Compose.

#### Scenario: Reviewer runs one guided entrypoint
- **WHEN** a reviewer executes the documented reviewer bootstrap script
- **THEN** the repository SHALL prepare local reviewer configuration, start the API, Grafana, and mock notification receiver services, run smoke validation, and print the resulting access details without requiring manual Python or Grafana installation steps

#### Scenario: Services are reachable after startup
- **WHEN** the reviewer bootstrap flow finishes successfully
- **THEN** the API health endpoint, the Grafana web UI, and the local mock notification receiver SHALL all be reachable on their documented localhost URLs

#### Scenario: Reviewer ports are localhost-only
- **WHEN** the reviewer stack publishes its services
- **THEN** the API, Grafana, and mock notification receiver SHALL be bound to localhost rather than all network interfaces

### Requirement: Reviewer bootstrap SHALL validate and message the environment
The reviewer bootstrap flow SHALL tell the reviewer what is available after startup and confirm the environment is working before declaring success.

#### Scenario: Bootstrap runs smoke validation
- **WHEN** the reviewer bootstrap starts the stack
- **THEN** it SHALL run the documented smoke checks before reporting the environment as ready

#### Scenario: Smoke validation confirms team notification delivery
- **WHEN** the one-click runtime executes its smoke checks
- **THEN** the validation flow SHALL trigger a known alert and verify that the local mock notification receiver recorded the expected team-notification payload

#### Scenario: Bootstrap prints first-login details
- **WHEN** the reviewer bootstrap finishes successfully
- **THEN** it SHALL print the Grafana URL, Grafana admin credentials, selected provider mode, the local mock notification receiver URL, and the command needed to stop the stack

#### Scenario: Bootstrap avoids exposing non-demo API keys in terminal output
- **WHEN** the reviewer bootstrap completes with non-demo API-key values
- **THEN** it SHALL avoid printing raw API-key values and SHALL print only a safe reference to where that key is stored

## ADDED Requirements

### Requirement: One-click mode SHALL provide a default local team notification target
The one-click reviewer runtime SHALL provision the monitoring service with a working local team-notification webhook target so reviewers can observe automatic alert reporting without external dependencies.

#### Scenario: Demo webhook target is configured automatically
- **WHEN** the reviewer stack starts with its default local configuration
- **THEN** the monitoring service SHALL receive a default internal/local webhook URL for the mock notification receiver without requiring manual env edits

#### Scenario: Local team notification target remains reviewer-safe
- **WHEN** the mock notification receiver is started in the one-click runtime
- **THEN** it SHALL remain a localhost-only/demo component rather than an externally exposed production notification path
