## MODIFIED Requirements

### Requirement: Reviewer stack SHALL start with a single Docker Compose command
The repository SHALL provide a Docker Compose based runtime that allows a reviewer to start the monitoring API and Grafana through one guided bootstrap entrypoint that invokes Docker Compose.

#### Scenario: Reviewer runs one guided entrypoint
- **WHEN** a reviewer executes the documented reviewer bootstrap script
- **THEN** the repository SHALL prepare local reviewer configuration, start the API and Grafana services, run smoke validation, and print the resulting access details without requiring manual Python or Grafana installation steps

#### Scenario: Services are reachable after startup
- **WHEN** the reviewer bootstrap flow finishes successfully
- **THEN** the API health endpoint and the Grafana web UI SHALL both be reachable on their documented localhost URLs

#### Scenario: Reviewer ports are localhost-only
- **WHEN** the reviewer stack publishes its services
- **THEN** the API and Grafana services SHALL be bound to localhost rather than all network interfaces

### Requirement: One-click mode SHALL preserve secured API access
The one-click reviewer runtime SHALL keep API-key protection enabled for secured monitoring endpoints while ensuring the provisioned dashboard can access them successfully.

#### Scenario: Grafana requests include the configured API key
- **WHEN** Grafana queries the API in one-click mode
- **THEN** the datasource configuration SHALL send the same API key value that the API service expects for `/metrics`, `/alerts`, and `/decision`

#### Scenario: Health remains publicly reachable
- **WHEN** the reviewer accesses the API health endpoint in one-click mode
- **THEN** the endpoint SHALL remain reachable without an API key

#### Scenario: One-click mode uses demo-only local credentials by default
- **WHEN** the reviewer stack starts with its default local configuration
- **THEN** the API key and Grafana admin credentials SHALL be clearly documented as demo-only local values and SHALL not require the reviewer to invent credentials manually

## ADDED Requirements

### Requirement: Reviewer bootstrap SHALL support provider-mode selection safely
The reviewer bootstrap flow SHALL let the reviewer choose between local decision guidance and optional external-provider-backed narrative enhancement without weakening the local-safe defaults.

#### Scenario: Reviewer selects local mode
- **WHEN** the reviewer chooses local mode
- **THEN** the bootstrap flow SHALL configure the stack without requiring any external provider API key

#### Scenario: Reviewer selects external mode
- **WHEN** the reviewer chooses external mode
- **THEN** the bootstrap flow SHALL offer the provider choices `openai`, `anthropic`, and `google`, collect the provider model and API key, and configure the runtime accordingly

#### Scenario: Missing external API key falls back to local mode
- **WHEN** the reviewer chooses external mode but does not provide a valid API key
- **THEN** the bootstrap flow SHALL fall back to local mode rather than leaving the runtime half-configured

#### Scenario: Bootstrap stores reviewer-local secrets outside committed files
- **WHEN** the reviewer bootstrap writes provider or API-key configuration
- **THEN** it SHALL write those values only to a gitignored reviewer-local env file or runtime environment, not to committed repository files

#### Scenario: Reviewer-local env file permissions are restricted
- **WHEN** the reviewer bootstrap writes a reviewer-local env file
- **THEN** the file SHALL be permission-restricted to owner read/write only

### Requirement: Reviewer bootstrap SHALL validate and message the environment
The reviewer bootstrap flow SHALL tell the reviewer what is available after startup and confirm the environment is working before declaring success.

#### Scenario: Bootstrap runs smoke validation
- **WHEN** the reviewer bootstrap starts the stack
- **THEN** it SHALL run the documented smoke checks before reporting the environment as ready

#### Scenario: Bootstrap prints first-login details
- **WHEN** the reviewer bootstrap finishes successfully
- **THEN** it SHALL print the Grafana URL, Grafana admin credentials, selected provider mode, and the command needed to stop the stack

#### Scenario: Bootstrap avoids exposing non-demo API keys in terminal output
- **WHEN** the reviewer bootstrap completes with non-demo API-key values
- **THEN** it SHALL avoid printing raw API-key values and SHALL print only a safe reference to where that key is stored
