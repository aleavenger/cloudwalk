## Purpose

Define one-click reviewer runtime expectations so evaluators can run API and Grafana locally with secure demo defaults and minimal setup.

## Requirements

### Requirement: Reviewer stack SHALL start with a single Docker Compose command
The repository SHALL provide a Docker Compose based runtime that allows a reviewer to start the monitoring API and Grafana with one command.

#### Scenario: Reviewer runs one command
- **WHEN** a reviewer executes the documented Docker Compose startup command
- **THEN** the repository SHALL start the API and Grafana services without requiring manual Python or Grafana installation steps

#### Scenario: Services are reachable after startup
- **WHEN** the Docker Compose stack finishes starting
- **THEN** the API health endpoint and the Grafana web UI SHALL both be reachable on their documented localhost URLs

#### Scenario: Reviewer ports are localhost-only
- **WHEN** the reviewer stack publishes its services
- **THEN** the API and Grafana services SHALL be bound to localhost rather than all network interfaces

### Requirement: One-click mode SHALL preserve secured API access
The one-click reviewer runtime SHALL keep API-key protection enabled for secured monitoring endpoints while ensuring the provisioned dashboard can access them successfully.

#### Scenario: Grafana requests include the configured API key
- **WHEN** Grafana queries the API in one-click mode
- **THEN** the datasource configuration SHALL send the same API key value that the API service expects for `/metrics` and `/alerts`

#### Scenario: Health remains publicly reachable
- **WHEN** the reviewer accesses the API health endpoint in one-click mode
- **THEN** the endpoint SHALL remain reachable without an API key

#### Scenario: One-click mode uses demo-only local credentials
- **WHEN** the reviewer stack starts with its default configuration
- **THEN** the API key and Grafana admin credentials SHALL be clearly documented as demo-only local values and SHALL not require the reviewer to invent credentials manually
