## Context

The repository already includes the core monitoring submission: a FastAPI service, analysis scripts, SQL artifacts, generated report assets, and a Grafana dashboard JSON. What it lacks is packaging for a reviewer who just wants to run the demo quickly. At the moment, the reviewer must install Python dependencies manually, generate the derived artifacts manually, install the Grafana Infinity plugin manually, and import/configure the dashboard manually.

This change is cross-cutting because it touches runtime packaging, documentation, dashboard setup, and environment wiring. It also changes the reviewer-facing behavior of the existing visualization/reporting capability by making the Docker Compose flow the primary launch path.

## Goals / Non-Goals

**Goals:**
- Provide a single-command reviewer experience using Docker Compose.
- Start both the FastAPI service and Grafana in a reproducible local environment.
- Automatically generate checkout anomaly CSV outputs and SVG charts before the API starts.
- Provision Grafana so the datasource and dashboard are available without manual UI configuration.
- Keep API authentication enabled in one-click mode and wire the same key into Grafana datasource requests.
- Preserve the existing API contracts, monitoring logic, and report content.

**Non-Goals:**
- Deploying the application to cloud or production infrastructure.
- Replacing the current manual workflow entirely; it remains a fallback path.
- Redesigning the monitoring API, anomaly engine, or dashboard semantics.
- Introducing additional backing services such as Prometheus or a database.

## Decisions

### Use Docker Compose as the primary reviewer entrypoint
The change will make `docker compose up --build` the canonical launch path. This reduces reviewer friction and avoids host-level Python packaging problems already present in the current environment.

Alternative considered:
- Bootstrap shell script only: simpler to author, but still depends on local Python tooling and Grafana availability.
- Manual setup plus better docs: lower effort, but does not achieve one-click reviewer setup.

### Add a dedicated API container with startup bootstrap script
The API service will run in a container that installs pinned Python dependencies, runs the checkout analysis and chart generation scripts, and then starts `uvicorn`. This ensures required report-side artifacts exist without a separate manual step.

Alternative considered:
- Pre-commit generated assets only: still leaves the reviewer without proof that startup is reproducible.
- Separate one-shot init container: cleaner separation, but unnecessary complexity for this repo.

### Provision Grafana instead of relying on manual UI setup
Grafana will be configured through provisioning files for:
- datasource creation using `yesoreyeram-infinity-datasource`
- dashboard auto-import using the existing JSON asset

The compose setup will also pin the plugin version used by the reviewer environment.
Locked behavior:
- Grafana datasource URL inside Compose uses `http://api:8000`, not `127.0.0.1`
- the existing repo dashboard JSON remains the human-readable source asset for the manual path
- one-click mode provisions a Compose-specific dashboard or templated datasource configuration that targets the internal service URL

Alternative considered:
- Manual import instructions only: does not satisfy the one-click goal.

### Enable API key protection by default in one-click mode
One-click mode will set `MONITORING_API_KEY` in the API container and configure the Grafana datasource to send `X-API-Key`. This preserves the current security posture while keeping the reviewer flow seamless.

Locked security defaults:
- the one-click stack uses a committed demo-only API key value such as `reviewer-local-demo-key`
- README labels the key as local-only and non-secret
- the key is acceptable only because the API and Grafana ports are published on localhost only
- no real secrets or personal credentials are committed for the reviewer flow

Alternative considered:
- Disable API key by default for convenience: easier to wire, but less aligned with the current secured runtime behavior.

### Bind reviewer-facing ports to localhost
Docker Compose will publish the API and Grafana ports on localhost only so the one-click setup remains local-safe by default.

Locked runtime exposure:
- publish API as `127.0.0.1:8000:8000`
- publish Grafana as `127.0.0.1:3000:3000`
- keep services on an internal Compose network for container-to-container traffic

Alternative considered:
- Publish on all interfaces: simpler compose syntax, but weaker default safety.

### Gate startup on service readiness and keep generated outputs visible on the host
The reviewer experience should not depend on lucky timing. The stack will use healthchecks and explicit startup ordering, and the generated artifacts must appear in the repository working tree so the reviewer can inspect them directly.

Locked behavior:
- API container healthcheck uses `GET /health`
- Grafana waits for the API to become healthy before starting datasource/dashboard dependent checks
- reviewer-facing smoke checks wait for both API and Grafana readiness, not just container start
- `report/`, `charts/`, and `logs/` are mounted so generated outputs remain visible on the host after startup
- source code and static repo inputs are mounted read-only where practical for the one-click stack

Alternative considered:
- fire-and-forget container startup: simpler, but too likely to present empty/broken panels immediately after `docker compose up`

### Use deterministic Grafana admin credentials for the demo stack
The one-click flow must avoid an extra discovery step at login.

Locked credentials:
- `GF_SECURITY_ADMIN_USER=admin`
- `GF_SECURITY_ADMIN_PASSWORD=admin`
- README calls out that these are demo-only local credentials

## Risks / Trade-offs

- [Compose startup depends on Docker availability] -> Mitigation: keep the existing manual README flow as fallback.
- [Grafana plugin installation may require network access during startup/build] -> Mitigation: pin the exact plugin version and document the expectation clearly.
- [Bootstrap script failures could hide the actual app startup issue] -> Mitigation: make the bootstrap script fail fast and stop container startup on errors.
- [Compose adds more files to maintain] -> Mitigation: keep the stack minimal with only API and Grafana services.
- [Demo credentials are committed in repo] -> Mitigation: restrict published ports to localhost, document them as non-secret demo values, and avoid reusing them anywhere outside the reviewer stack.

## Migration Plan

There is no data migration. The implementation adds packaging/orchestration files around the current repository.

Execution order:
1. Add Docker Compose, API container image, and startup bootstrap script.
2. Add Grafana provisioning for datasource and dashboard import using the internal Compose API URL.
3. Add environment wiring for demo-only API key, deterministic Grafana admin credentials, localhost-bound ports, and readiness checks.
4. Mount generated-output directories so charts, logs, and report artifacts remain visible on the host.
5. Update README to make Docker Compose the primary reviewer flow and manual setup the fallback.
6. Add smoke-test guidance or checks for compose startup, API health, generated outputs, and Grafana reachability.

Rollback strategy:
- Remove the orchestration and provisioning files and keep the existing manual startup path unchanged.

## Open Questions

None. The implementation can proceed with the decisions above.
