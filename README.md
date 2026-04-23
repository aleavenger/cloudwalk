# CloudWalk Monitoring Test Submission

This repository implements the CloudWalk monitoring analyst challenge with:
- checkout anomaly analysis (SQL + charts + findings),
- a FastAPI transaction monitoring service with alert recommendations,
- Grafana dashboard visualization,
- local-safe defaults for reviewer execution.

## One-Step Reviewer Bootstrap (Primary)

Prerequisites:
- Docker Engine
- Docker Compose (v2, `docker compose`)
- Network access to pull images and the pinned Grafana Infinity plugin

Single command startup:

```bash
./scripts/reviewer_start.sh
```

Services:
- API: `http://127.0.0.1:8000`
- Grafana: `http://127.0.0.1:3000`
- Mock team receiver: `http://127.0.0.1:8010`

Bootstrap behavior:
- creates `.env.reviewer` from `.env.example` and sets owner-only permissions (`chmod 600`)
- prompts for decision mode (`local` or `external`), defaulting to `external` for reviewer narrative polish
- if `external`: prompts provider (`openai`, `anthropic`, `google`), model, and API key
- falls back to deterministic `local` mode when external key is not provided
- starts API + Grafana + mock team receiver with `docker compose --env-file .env.reviewer up --build -d`
- runs `./scripts/smoke_one_click.sh`
- prints first-login details and safe stop command

Default demo credentials:
- Grafana user: `admin`
- Grafana password: `admin`
- API key header: `X-API-Key: reviewer-local-demo-key`
- Grafana anonymous dashboard access: enabled (Viewer role) for local demo reliability

Demo key notice:
- `reviewer-local-demo-key` is a local demo value only.
- It is intentionally committed for evaluator convenience and is safe only because ports are bound to `127.0.0.1`.
- The bootstrap script prints raw monitoring API keys only for this demo value.
- For non-demo keys, bootstrap output shows only `MONITORING_API_KEY` reference in `.env.reviewer`.

The stack automatically:
- generates `database/report/checkout_1_anomaly.csv` and `database/report/checkout_2_anomaly.csv`,
- generates `charts/checkout_1.svg` and `charts/checkout_2.svg`,
- provisions a local mock team-notification receiver for end-to-end alert delivery checks,
- provisions Grafana datasource and dashboard from `grafana/dashboard.json`.

Reviewer-facing deliverables:
- presentation deck: `report/presentation.md`
- technical report: `report/technical_report.md`
- methodology reference: `docs/monitoring-methodology.md`

Smoke checks after startup:

```bash
./scripts/smoke_one_click.sh
```

This smoke script also enforces the Grafana dashboard provisioning contract (query format/parser/typed columns) to catch "No data" regressions.
It also triggers a known alert and verifies the local mock team receiver recorded the webhook payload.
When Playwright tooling is available, smoke checks also run `./scripts/check_grafana_dashboard_playwright.sh` for reviewer-visible dashboard validation.

Optional config override:

```bash
cp .env.example .env
docker compose up --build
```

`API_PORT` changes only the host binding (`127.0.0.1:<API_PORT>`). The internal Compose service URL stays `http://api:8000`.

## Security and Runtime Defaults

- Published ports are localhost-only:
  - `127.0.0.1:8000` for API
  - `127.0.0.1:3000` for Grafana
  - `127.0.0.1:8010` for the mock team receiver
- `/health` is public.
- `/monitor`, `/monitor/transaction`, `/metrics`, `/metrics/focus`, `/alerts`, `/decision`, `/decision/focus`, and `/decision/forecast/focus` require `X-API-Key` when `MONITORING_API_KEY` is set (enabled by default in one-click mode).
- Output directories are mounted to host:
  - `report/`
  - `charts/`
  - `logs/`
- Formal alerts always write aggregate metadata to `logs/alerts.log` and, in one-click mode, also deliver a webhook payload to the local mock team receiver.

Monitoring ingestion paths:
- `POST /monitor`: aggregate minute-window replay endpoint used by the dataset, smoke tests, and dashboard-linked monitoring flow.
- `POST /monitor/transaction`: single-event endpoint that folds one transaction into its minute bucket and evaluates the resulting window through the same anomaly engine.
- `GET /metrics/recent?days=5`: compatibility endpoint for latest-anchored metrics slices.
- `GET /metrics/focus?bucket=hour|minute`: returns the newest eligible data cluster for dashboard charts; Grafana uses `bucket=hour`.
- `GET /decision/focus`: returns decision, evidence, business impact, and forecast for the selected dashboard focus cluster.
- `GET /decision/forecast/focus`: returns the focused forecast as relative-horizon rows (`+5m`, `+10m`, ...) for the "What Could Get Worse In The Forecast Window" panel.

Decision guidance modes:
- `DECISION_ENGINE_MODE=local` (default): deterministic local scoring, ranking, and forecast.
- `DECISION_ENGINE_MODE=external`: local scoring remains authoritative; external provider may rewrite only `summary`, `top_recommendation`, `problem_explanation`, and `forecast_explanation`.
- Supported external providers: `openai`, `anthropic`, `google`.
- In compose mode, defaults are `EXTERNAL_AI_PROVIDER=openai` and `EXTERNAL_AI_MODEL=gpt-4o-mini` when those variables are not set.
- Default `DECISION_MIN_HISTORY_POINTS=1` is demo-oriented and `/decision` shows a forecast warning when this test value is used; production recommendation is `5`.
- For `openai`, optional `EXTERNAL_AI_BASE_URL` enables OpenAI-compatible endpoints (for example `https://openrouter.ai/api/v1`); leave it empty to use official OpenAI.
- External failures safely fall back to local output and expose sanitized provider status in `/decision`.

Business-impact fields in `/decision`:
- top-level `business_impact` includes `top_metric`, `domain_label`, `likely_owner`, `above_normal_rate`, `warning_gap_rate`, `excess_transactions_now`, and `projected_excess_transactions_horizon`.
- each priority item includes per-metric `above_normal_rate`, `forecast_above_normal_rate`, `warning_gap_rate`, and excess-transaction projections.
- `projected_excess_transactions_horizon` uses current window volume as a deterministic projection proxy.

Decision-state semantics:
- `act_now`: current warning/critical risk in any monitored metric.
- `watch`: no current warning/critical, but current info-level risk or forecasted elevation.
- `normal`: no current or forecasted elevated risk.
- `watch` is predictive guidance only and does not create formal alert-history records.

OpenSpec CLI wrapper:
- use `./scripts/openspec.sh ...` to prefer `.venv/bin/openspec` and fall back to PATH safely.

## Grafana URL Distinction

- One-click compose mode uses internal container URL: `http://api:8000`.
- Manual/local-host mode (outside compose) should use `http://127.0.0.1:8000`.

The provisioned dashboard is optimized for compose mode and expects the internal API URL.
Datasource provisioning also allowlists `http://api:8000` for Infinity URL mode.
The rendered dashboard time range is absolute and follows the newest eligible data cluster, extending through the forecast horizon when forecast data is available.
The dashboard is organized in business reading order: current priority, business impact, forecast/evidence, trend context, formal alert history, then deeper metric-ranking detail.
The "What Could Get Worse In The Forecast Window" panel is the exception: it uses a relative horizon axis so short-horizon forecast bars stay readable instead of being compressed by the dashboard-wide cluster window.
Auth-code evidence is rendered as readable dashboard strings such as `51 Insufficient funds x6` while the API still keeps the structured top-code tuples for machine consumers.
Decision/business-impact panels render confidence and rate values with percent-based human-readable units while API fields remain raw numeric values.

## Manual Setup (Fallback)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m scripts.checkout_analysis
python -m scripts.generate_checkout_charts
export MONITORING_API_KEY="reviewer-local-demo-key"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Manual Grafana fallback:
- Install plugin: `grafana cli plugins install yesoreyeram-infinity-datasource 3.6.0`.
- If you run Grafana outside compose, update dashboard query URLs from `http://api:8000/...` to `http://127.0.0.1:8000/...` before import.

Manual notification fallback:
- By default, manual local API runs use log-only alert reporting.
- To test team delivery outside compose, set `TEAM_NOTIFICATION_WEBHOOK_URL` to a reachable webhook target before starting the API.

## Project Structure

- `app/`: FastAPI service, anomaly engine, data loading, security, notifier.
- `scripts/`: analysis/chart generation and smoke checks.
- `sql/`: checkout and transaction analysis queries.
- `grafana/`: dashboard JSON and provisioning files.
- `database/`: challenge CSV datasets, `monitoring-test.md`, and generated anomaly CSV outputs.
- `report/`: technical report markdown.
- `charts/`: generated SVG charts.
- `logs/`: generated alert log output.
- `tests/`: API/security test suite.

## Repository Contracts

Behavior and safety contracts are documented in:
- `RULES.md` (canonical AI/shared rules baseline)
- `INVARIANTS.md` (strict system invariants)
- `SYSTEM_MAP.md` (architecture and runtime map)
- `AI_GUARDRAILS.md` (AI change safety constraints)
- `docs/monitoring-methodology.md` (end-to-end logic and result-derivation methodology)

Connected AI adapter files:
- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.github/copilot-instructions.md`
