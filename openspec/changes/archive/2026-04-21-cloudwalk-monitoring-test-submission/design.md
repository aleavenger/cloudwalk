## Context

The repository currently contains only the CloudWalk challenge brief and the four CSV datasets. The submission needs to cover two distinct but connected outcomes: a checkout anomaly analysis deliverable and a runnable transaction monitoring system with alerts, charts, and reporting. The solution must look credible for a monitoring analyst role, favoring operational clarity, reproducibility, and low-noise alerting over unnecessary platform complexity.

The input datasets naturally split into:
- hourly checkout comparisons in `checkout_1.csv` and `checkout_2.csv`
- minute-level transaction status totals in `transactions.csv`
- minute-level authorization code totals in `transactions_auth_codes.csv`

The role and brief both emphasize SQL, dashboards, and practical alerting. The design therefore needs to keep the implementation compact enough to finish quickly while still demonstrating monitoring judgment.

## Goals / Non-Goals

**Goals:**
- Produce a self-contained submission that can be reviewed locally from a single repository.
- Implement a FastAPI monitoring service that exposes health, metrics, alert history, and anomaly recommendation endpoints.
- Use SQL as a first-class analysis artifact for both checkout and transaction datasets.
- Use Grafana as the visualization layer so the submission matches the job’s monitoring-tool expectations.
- Implement a hybrid anomaly model with baseline comparison, severity assignment, low-volume suppression, and cooldown-based deduplication.
- Use authorization code data to improve anomaly explanation and operator triage.
- Provide a written report and runnable instructions that explain findings, decisions, and limitations.

**Non-Goals:**
- Building a production deployment pipeline or hosted environment.
- Training a machine learning model or introducing external data stores.
- Supporting arbitrary streaming inputs beyond the CSV-backed and request-backed monitoring workflow.
- Turning Grafana setup into a fully automated infrastructure provisioning project.

## Decisions

### Use FastAPI as the application surface
FastAPI provides a small, readable Python service with clear JSON contracts and low ceremony for local startup. It is a better fit than Flask for typed request and response models, and it keeps the service credible for an operations-facing technical submission.

Locked API contracts:
- `POST /monitor` request body:
  - `window_end` (string, required, `YYYY-MM-DD HH:MM:SS`)
  - `approved`, `denied`, `failed`, `reversed`, `backend_reversed`, `refunded` (integers, required, `>= 0`)
  - `auth_code_counts` (object map `{string:int}`, optional)
- `POST /monitor` response body:
  - `window_end` (string)
  - `recommendation` (`alert` | `no_alert`)
  - `severity` (`none` | `info` | `warning` | `critical`)
  - `triggered_metrics` (array of `denied` | `failed` | `reversed`)
  - `rates` (object with `denied_rate`, `failed_rate`, `reversed_rate`)
  - `baseline_rates` (object with `denied_rate`, `failed_rate`, `reversed_rate`)
  - `notification_sent` (boolean)
  - `reason` (string)
- `GET /metrics` response body:
  - root object with `rows` array
  - each row includes `timestamp`, `total`, `approved_rate`, `denied_rate`, `failed_rate`, `reversed_rate`, `alert_severity`
- `GET /alerts` response body:
  - root object with `alerts` array
  - each item includes `timestamp`, `severity`, `triggered_metrics`, `rates`, `baseline_rates`, `notification_status`, `reason`
- validation behavior:
  - invalid payload fields return HTTP `422` with FastAPI validation error structure
- `GET /health` returns HTTP `200` with `{ "status": "ok" }`

Locked access controls:
- default bind address for local run: `127.0.0.1`
- `POST /monitor`, `GET /metrics`, and `GET /alerts` require header `X-API-Key` when `MONITORING_API_KEY` is set
- `GET /health` remains unauthenticated for local checks
- missing or invalid API key returns HTTP `401`

Locked payload safety limits:
- max request body size for `POST /monitor`: `64 KB`
- max per-field count value: `1_000_000`
- max `auth_code_counts` keys: `32`
- max auth code key length: `16`
- values outside these bounds return HTTP `422`

Alternative considered:
- Flask: simpler, but weaker typing and less structured API contracts.
- Streamlit-only app: faster for visuals, but weaker demonstration of a monitoring service architecture.

### Keep CSV files as the canonical data source and precompute in application memory
The challenge datasets are small, fixed snapshots. Loading them into memory at startup keeps the implementation simple, reproducible, and dependency-light while still allowing SQL artifacts to describe the intended analysis logic.

Alternative considered:
- SQLite ingestion: useful for querying, but adds setup and persistence decisions without improving the submission materially.

### Split the solution into analysis, service, dashboard, and reporting layers
The submission needs both insight generation and a runnable system. Separating these concerns allows the implementation to stay clear:
- SQL files define reproducible analysis logic
- FastAPI exposes metrics and alert decisions
- Grafana visualizes current and historical behavior
- report assets explain what was found and why the alerting logic is appropriate

Alternative considered:
- Put everything into a notebook: faster for exploration, but weaker for endpoint design and monitoring realism.

### Use a hybrid anomaly model instead of fixed thresholds alone
Static thresholds are easy to implement but too noisy or misleading across metrics with very different baselines. The alert model will compare current rates for `denied`, `failed`, and `reversed` against a rolling baseline while also enforcing minimum absolute floors and minimum total-volume conditions. This balances sensitivity and false-positive control.

Locked behavior:
- compute per-minute total volume and status-specific rates
- compute baseline as the mean of the previous `60` complete minutes for each metric
- compare current window rate against baseline via fixed multipliers
- apply severity bands (`INFO`, `WARNING`, `CRITICAL`)
- suppress low-volume windows
- deduplicate repeated alerts during a cooldown period

Locked parameters:
- `minimum_total_count = 80`
- `minimum_metric_count = 3`
- floor rates:
  - denied: `0.08`
  - failed: `0.02`
  - reversed: `0.03`
- warning condition for a metric: `current_rate >= max(floor_rate, baseline_rate * 2.0)`
- critical condition for a metric: `current_rate >= max(floor_rate * 1.5, baseline_rate * 3.0)`
- cooldown key: metric + severity
- cooldown duration: `10` minutes
- escalation rule: allow a higher severity during cooldown; suppress duplicate same-or-lower severity

Alternative considered:
- pure percentile thresholds: simpler, but less adaptive to changing local windows
- supervised model: overkill for the scope and unsupported by the provided data volume

### Use authorization codes as triage enrichment, not as the primary anomaly trigger
The auth-code dataset is useful and often skipped by weaker submissions. It will be used to describe anomalous windows and show which code families dominate a spike. It will not become the sole alert signal because the challenge requirements are explicitly framed around transaction statuses.

Alternative considered:
- alert directly on auth-code spikes: interesting, but not aligned to the brief’s primary requirements

### Use Grafana with API-fed JSON metrics rather than introducing a separate time-series backend
The job posting references Grafana, so using it strengthens the operational framing. Instead of adding Prometheus or a database, the service will expose JSON endpoints tailored for dashboard consumption, and the repository will include a ready-to-import dashboard JSON plus screenshots.

Locked Grafana integration:
- Grafana datasource plugin: `yesoreyeram-infinity-datasource`
- metrics panels query `GET /metrics` and map fields from `rows[*]`
- alert table panel queries `GET /alerts` and maps fields from `alerts[*]`
- all time-series panels use `timestamp` as time field and explicit numeric fields from the contract
- README must include plugin installation and datasource configuration steps
- README must pin plugin version and installation command used for reproducible setup

Alternative considered:
- Plotly embedded charts only: simpler, but weaker role alignment
- Prometheus exporter plus scrape config: stronger ops realism, but too much setup for the scope

### Record notifications through a pluggable sink with a default local logger implementation
The brief asks for automatic reporting to teams. To satisfy that requirement without external credentials, the service will normalize alert payloads through a notifier interface and persist delivery attempts in alert history, with a default implementation that logs the payload locally.

Locked logging safety rules:
- log only aggregated fields (`timestamp`, `severity`, `triggered_metrics`, rate summaries, notification status)
- do not log raw request bodies
- do not log API keys, environment variables, or stack traces in normal operation
- keep alert log file local and gitignored by default

Alternative considered:
- console print only: too weak to demonstrate reporting flow
- hardcoded Slack integration: brittle and credential-dependent

## Risks / Trade-offs

- [Grafana adds local setup friction] → Mitigation: keep the data source contract simple, commit a ready-to-import dashboard JSON, and include screenshot-backed report evidence.
- [Hybrid thresholds may still need tuning] → Mitigation: lock initial thresholds in the design, justify them in the report, and cover edge cases with tests.
- [CSV-backed “real time” is simulated rather than live] → Mitigation: expose request-driven monitoring endpoints and describe the historical replay model explicitly.
- [Authorization codes have limited semantic detail] → Mitigation: use them for distribution shifts and drilldown context rather than unsupported business interpretation.
- [Single-process in-memory alert state is not production-grade] → Mitigation: keep that limitation explicit and treat it as acceptable for a local technical submission.

## Migration Plan

There is no production migration. Implementation will be introduced as a new local submission package in the repository.

Execution order:
1. Add SQL analysis artifacts for checkout and transaction datasets.
2. Implement the FastAPI data loading, aggregation, and alerting modules.
3. Add API models and endpoints for health, metrics, alert history, and monitor recommendations using the locked schemas.
4. Add Grafana dashboard JSON, datasource assumptions, pinned plugin version, and import workflow documentation.
5. Add the technical report, screenshots, and startup instructions.
6. Add focused tests for alerting behavior, endpoint contracts, known dataset anomaly windows, access controls, and payload limits.

Rollback strategy:
- Revert the added submission files if needed; no shared state or schema migration is involved.

## Open Questions

None. The implementation will proceed with the decisions above.
