# SYSTEM MAP: cloudwalk

Date: 2026-04-23

## Tech Stack
- Backend: Python + FastAPI (`app/main.py`).
- Validation: Pydantic models (`app/models.py`).
- Data source: CSV datasets loaded at startup (`app/data_loader.py`).
- Alert engine: baseline + threshold + cooldown evaluator (`app/anomaly.py`).
- Decision engine: local deterministic prioritization + forecast with optional external narrative rewrite for readability polish, not core decision authority (`app/decision.py`).
- Notification sink: append-only JSON lines log plus optional webhook delivery (`app/notifier.py`).
- Infra: Docker Compose with API + Grafana + mock team receiver (`docker-compose.yml`).

## Directory Structure
- `app/` - API app, settings, security guard, anomaly engine, notifier, mock team receiver, loaders, schemas.
- `database/` - source CSV datasets and generated report CSV files.
- `scripts/` - anomaly report generation, chart generation, smoke checks.
- `scripts/reviewer_start.sh` - one-step reviewer bootstrap (env prep, compose up, smoke checks, first-login output).
- `scripts/reviewer_start.ps1` - Windows PowerShell launcher that runs the same bootstrap through Git Bash.
- `charts/` - generated SVG visualizations.
- `grafana/` - dashboard JSON and provisioning config.
- `docker/` - API and Grafana image definitions and startup entrypoint.
- `tests/` - API and contract-level tests.
- `report/` - technical report narrative.

## Entry Points
- App bootstrap: `app/main.py` (`create_app`).
- Container bootstrap: `docker/api-entrypoint.sh`.
- Reviewer bootstrap: `scripts/reviewer_start.sh`.
- Windows reviewer bootstrap launcher: `scripts/reviewer_start.ps1`.
- Runtime server: `uvicorn app.main:app`.

## Architecture Pattern
- Checkout artifact flow:
  - `scripts/checkout_analysis.py` derives checkout anomaly rows with blended `baseline`, deviation fields, and investigation metadata (`is_material`, `direction`, `zero_gap`, `severity_score`)
  - `scripts/generate_checkout_charts.py` reads those anomaly CSVs and renders investigation-first SVGs for reviewer evidence with `Today` vs `Expected`, top summary cards (`Today total`, `Expected total`, `Net deviation`, `Investigate first`), a verdict badge, and a `Why this verdict` evidence sidebar
- Startup flow:
  - load settings from env (`app/config.py`)
  - load historical rows from CSV (`load_transactions`)
  - initialize `AlertEngine` and in-memory runtime state
  - build initial metrics timeline from historical rows
- Request flow:
  - `MonitorPayloadLimitMiddleware` enforces max body size for `/monitor` and `/monitor/transaction`
  - API key dependency guard validates `X-API-Key` when key configured
  - `/monitor` evaluates aggregate minute-window counts against baseline + floors + multipliers
  - `/monitor/transaction` normalizes a single event into its minute bucket and reuses the same alert workflow
  - alert-worthy events are logged locally and may also be delivered to the configured webhook target before being appended to in-memory `alert_history`
- `/metrics` exposes historical + upserted runtime metrics rows
- `/metrics/recent` exposes a latest-anchored subset of metrics rows for compatibility callers
- `/metrics/focus` exposes the newest eligible dashboard-focus cluster in minute or hourly buckets
- `/alerts` exposes in-memory alert history
- `/decision` computes operator-facing status/ranking/forecast/evidence from runtime state
- `/decision/focus` computes the same decision payload for the selected dashboard-focus cluster
- `/decision/forecast/focus` exposes the focused forecast as relative-horizon chart rows for the Grafana forecast panel
- auth-code evidence is stored as top-k tuples and also exposed as readable display strings for Grafana tables
- decision response includes deterministic business-impact fields (`above_normal`, warning-gap, excess-transaction projections, owner/domain mapping) derived from local metrics
- optional external provider path rewrites only narrative fields (`summary`, `top_recommendation`, `problem_explanation`, `forecast_explanation`) with sanitized fallback state on errors; ranking, thresholds, risk, forecast, and business-impact numerics remain local
- when `DECISION_MIN_HISTORY_POINTS=1`, forecast text includes an explicit test/demo warning that recommends `5` for stronger forecast reliability

## Public API Endpoints
- `GET /health` - liveness check (public)
- `POST /monitor` - evaluate a time window and optionally emit alert log
- `POST /monitor/transaction` - fold a single transaction event into its minute bucket and evaluate alert recommendation
- `GET /metrics` - return time-series metrics rows
- `GET /metrics/recent` - return latest-anchored metrics rows for the requested recent-day window
- `GET /metrics/focus` - return dashboard-focus metrics rows for the selected cluster and bucket
- `GET /alerts` - return alert history records
- `GET /decision` - return decision snapshot (status, priority queue, forecast, evidence, provider state)
- `GET /decision/focus` - return a decision snapshot scoped to the selected dashboard-focus cluster
- `GET /decision/forecast/focus` - return relative-horizon forecast chart rows for the selected dashboard-focus cluster

## Configuration Surface
From environment (`app/config.py`, `.env.example`, `docker-compose.yml`):
- API/runtime: `HOST`, `PORT`, `DATA_DIR`
- Auth: `MONITORING_API_KEY`
- Team notification: `TEAM_NOTIFICATION_WEBHOOK_URL`, `TEAM_NOTIFICATION_TIMEOUT_SECONDS`
- Request safety: `MAX_MONITOR_REQUEST_BYTES`, `MAX_COUNT_VALUE`, `MAX_AUTH_CODE_KEYS`, `MAX_AUTH_CODE_KEY_LENGTH`
- Baseline/noise control: `MINIMUM_TOTAL_COUNT`, `MINIMUM_METRIC_COUNT`, `BASELINE_WINDOW_MINUTES`, `COOLDOWN_MINUTES`
- Threshold tuning: `FLOOR_RATE_DENIED`, `FLOOR_RATE_FAILED`, `FLOOR_RATE_REVERSED`, `WARNING_MULTIPLIER`, `CRITICAL_MULTIPLIER`
- Decision runtime: `DECISION_ENGINE_MODE`, `DECISION_LOOKBACK_MINUTES`, `DECISION_FORECAST_HORIZON_MINUTES`, `DECISION_FORECAST_STEP_MINUTES`, `DECISION_MIN_HISTORY_POINTS`
- Optional external narrative: `EXTERNAL_AI_PROVIDER`, `EXTERNAL_AI_MODEL`, `EXTERNAL_AI_API_KEY`, `EXTERNAL_AI_BASE_URL`, `EXTERNAL_AI_TIMEOUT_SECONDS` (interactive reviewer bootstrap keeps OpenAI visible as an optional narrative mode; raw compose defaults remain provider `openai`, model `gpt-4o-mini` when model env is unset; empty base URL uses official OpenAI)
- Reviewer Grafana UX: `GRAFANA_ANONYMOUS_ENABLED`

## Data Flow and Persistence
- Persistent input: CSV files under `database/`.
- Persistent output:
  - `database/report/*.csv` generated by `scripts/checkout_analysis.py` as checkout anomaly tables for reviewer evidence
  - `charts/*.svg` generated by `scripts/generate_checkout_charts.py` as investigation-first checkout summaries for reviewer evidence, not Grafana datasource inputs
  - `logs/alerts.log` generated by `AlertNotifier`
  - `logs/team_notifications.jsonl` generated by the mock team receiver in one-click mode
  - `.env.reviewer` generated by `scripts/reviewer_start.sh` (gitignored, owner read/write only)
- In-memory runtime state (process-local):
  - loaded transaction rows
  - alert cooldown state
  - `alert_history`
  - `metrics_rows`
  - `auth_codes_by_timestamp`

## Grafana Provisioning Notes
- Datasource provisioning (`grafana/provisioning/datasources/cloudwalk.yaml`) sets custom `X-API-Key` header and explicit `allowedHosts` for API URLs used by Infinity URL-mode queries.
- Dashboard provisioning renders `grafana/dashboard.json` from `grafana/dashboard.template.json` with an absolute focus window derived from the newest eligible data cluster.
- Dashboard refresh is fixed at `30m` for reviewer clarity.
- Trend/volume charts query `/metrics/focus?bucket=hour`, decision tables query `/decision/focus`, and the forecast panel queries `/decision/forecast/focus`.
- When `DECISION_ENGINE_MODE=external`, page loads and refresh cycles can trigger repeated AI-backed narrative requests because multiple panels query `/decision/focus`.
- Metric visualizations are provisioned with Infinity backend parser plus explicit typed columns; time-series panels use timestamp+number fields and the forecast panel uses a string horizon axis with numeric series for Grafana 11 rendering.
- Decision and evidence tables consume backend-provided auth-code display fields rather than raw JSON arrays.
- Dashboard layout is decision-first and business-ordered: current priority first, then business impact, then forecast/evidence, then trend/traffic context, then formal alert history, deeper metric-ranking detail, and first-login guidance.
- Compose runtime enables Grafana anonymous viewer mode for local-review reliability (`GF_AUTH_ANONYMOUS_ENABLED=true`, role `Viewer`).
- Compose runtime also provisions a localhost-only mock receiver so formal alert webhook delivery can be demonstrated without external services.

## External Dependencies
- Docker + Docker Compose for one-click execution.
- Grafana image with Infinity plugin for dashboard data source.
- FastAPI/Uvicorn/Pydantic runtime packages.

## Complexity Hotspots
1. Alert thresholding and cooldown interactions in `app/anomaly.py`.
2. Runtime state consistency across anomaly + decision paths in `app/main.py`.
3. Forecast stability/interpretation with sparse history in `app/decision.py`.
4. Data quality assumptions from CSV input formatting (`timestamp`, status keys, auth code mapping).
5. Divergent behavior between compose mode (`api:8000` plus local mock receiver) and local-host mode (`127.0.0.1:8000`) for dashboard and notification verification.

## Known Risk Areas
1. Input spikes with very small totals can cause noisy alerts if volume gates are misconfigured.
2. If `MONITORING_API_KEY` is unset, protected endpoints become public by design.
3. Decision guidance can diverge from operator expectations when history is sparse; forecast confidence must be interpreted as heuristic.
4. `alert_history` is process-memory only and resets on restart.
5. Invalid or malformed CSV datasets can fail startup.
6. Webhook delivery can fail independently of anomaly evaluation, so alert-history fields must represent team delivery status honestly.
