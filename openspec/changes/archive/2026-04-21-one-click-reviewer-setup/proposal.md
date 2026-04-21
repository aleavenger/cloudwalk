## Why

The current repository is technically runnable, but reviewer setup still depends on manual Python environment creation, manual artifact generation, manual Grafana plugin installation, and manual dashboard wiring. This change is needed now to turn the submission into a true one-command demo so the evaluator can assess the work quickly without spending effort on local setup.

## What Changes

- Add a Docker Compose based reviewer workflow that starts the FastAPI service and Grafana with a single command.
- Add containerized bootstrap behavior so checkout analysis CSV outputs and chart assets are generated automatically before the API starts.
- Add Grafana provisioning so datasource configuration and dashboard import happen automatically instead of requiring manual setup.
- Update reviewer-facing documentation to make the Docker Compose path the primary setup flow and keep the manual path only as fallback.
- Add reviewer-safe runtime defaults: localhost-only published ports, deterministic demo-only credentials, readiness checks, and host-visible generated outputs.
- Preserve the existing API contracts and monitoring behavior while packaging them into a reproducible local demo environment.

## Capabilities

### New Capabilities
- `reviewer-one-click-runtime`: Provide a one-command local runtime that boots the API, generated artifacts, and Grafana for reviewer use.
- `containerized-submission-bootstrap`: Define the container startup behavior that prepares required submission artifacts before serving traffic.

### Modified Capabilities
- `monitoring-visualization-and-reporting`: Update the reviewer setup requirements so Grafana datasource and dashboard import are automated in one-click mode.

## Impact

- Adds Docker and Docker Compose orchestration assets, runtime scripts, and environment wiring.
- Changes the primary README setup path from manual local commands to a single containerized reviewer flow.
- Extends the existing dashboard/reporting capability with provisioning requirements while keeping current API endpoints and data contracts intact.
- Introduces explicit runtime security guardrails for the local demo stack rather than relying on implicit defaults.
