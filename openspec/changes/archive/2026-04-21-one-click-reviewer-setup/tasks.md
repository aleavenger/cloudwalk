## 1. Compose Runtime

- [x] 1.1 Add a `docker-compose.yml` that starts `api` and `grafana` services with localhost-bound ports.
- [x] 1.2 Add environment wiring for demo-only `MONITORING_API_KEY`, deterministic Grafana admin credentials, API host/port, and any required runtime limits in the compose stack.
- [x] 1.3 Add a reviewer-facing `.env.example` or equivalent compose env template for one-click startup and document which values are demo-only defaults.
- [x] 1.4 Add API and Grafana healthchecks plus Compose readiness/dependency wiring so the stack is considered ready only after health endpoints succeed.

## 2. API Container Bootstrap

- [x] 2.1 Add a Dockerfile for the FastAPI service with pinned dependency installation.
- [x] 2.2 Add a startup entrypoint script that runs checkout analysis and chart generation before launching `uvicorn`.
- [x] 2.3 Make the API container fail fast when bootstrap artifact generation fails.
- [x] 2.4 Ensure the one-click runtime preserves the current secured API behavior while keeping `/health` public.
- [x] 2.5 Mount `report/`, `charts/`, and `logs/` so generated outputs remain visible on the host after startup.

## 3. Grafana Provisioning

- [x] 3.1 Add Grafana provisioning files that create the Infinity datasource automatically.
- [x] 3.2 Wire the provisioned datasource to `http://api:8000/metrics` and `http://api:8000/alerts` and include the configured `X-API-Key` header.
- [x] 3.3 Add automatic dashboard provisioning for the existing `grafana/dashboard.json`.
- [x] 3.4 Pin the Infinity plugin version in the containerized reviewer setup.

## 4. Reviewer Documentation

- [x] 4.1 Rewrite the README so Docker Compose is the primary reviewer flow and the manual path is explicitly marked as fallback.
- [x] 4.2 Document the one-command startup, localhost URLs, default Grafana credentials, demo-only API key behavior, and expected health checks.
- [x] 4.3 Document the plugin/version assumptions, Docker prerequisites, and the internal-vs-manual API URL distinction for Grafana setup.

## 5. Verification

- [x] 5.1 Add smoke-check guidance or scripts for API health, `/metrics`, and Grafana reachability in one-click mode.
- [x] 5.2 Verify that startup generates the checkout anomaly CSV outputs and SVG charts automatically.
- [x] 5.3 Verify that Grafana comes up with datasource and dashboard available without manual UI configuration.
- [x] 5.4 Verify that the generated outputs are visible on the host after Docker Compose startup.
- [x] 5.5 Review the repository for one-click reviewer completeness, localhost-only exposure, and keep the current manual workflow available as fallback.
