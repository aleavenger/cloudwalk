# CloudWalk Monitoring Test Submission

This repository covers two linked challenge tracks:
- challenge 3.1: investigate checkout behavior with SQL, derived anomaly tables, and generated SVG charts to decide what should be investigated first
- challenge 3.2: implement a FastAPI transaction monitoring service with alert recommendations, reporting, and dashboard visualization
- local-safe defaults for reviewer execution

## Development Approach

This submission was built with AI assistance, but under explicit engineering constraints and close human review.

- AI was used to accelerate implementation, refactoring, and documentation iterations.
- Human review kept the final repository reviewer-safe by checking authenticated endpoints, bounded payload validation, deterministic alert rules, sanitized logging, and end-to-end behavior.
- Final validation was done against the challenge datasets, SQL outputs, generated charts, API contracts, automated tests, and smoke checks.
- Internal tool/process files and generated local logs are intentionally excluded from the submission view because they do not change runtime behavior or challenge evidence.

## One-Step Reviewer Bootstrap (Primary)

Prerequisites:
- Bash shell (`bash`) to run `./scripts/reviewer_start.sh`
- On Windows, use PowerShell + Git Bash and run `.\scripts\reviewer_start.ps1`
- Docker Engine
- Docker Compose (v2, `docker compose`)
- `curl`
- `python3`
- Network access to pull images and the pinned Grafana Infinity plugin

Single command startup:

```bash
./scripts/reviewer_start.sh
```

Windows (PowerShell):

```powershell
.\scripts\reviewer_start.ps1
```

Services:
- API: `http://127.0.0.1:8000`
- Grafana: `http://127.0.0.1:3000`
- Mock team receiver: `http://127.0.0.1:8010`

Bootstrap behavior:
- recreates `.env.reviewer` from `.env.example` on each run and sets owner-only permissions (`chmod 600`)
- prompts for decision mode (`local` or `external`), defaulting to `external` for reviewer narrative polish
- if `external` is selected: prompts provider (`openai`, `anthropic`, `google`), model, and API key
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

Clarification:
- `database/report/checkout_*_anomaly.csv` and `charts/checkout_*.svg` are offline reviewer artifacts for the first challenge investigation narrative.
- The checkout SVGs are investigation-first summaries: `Today` vs `Expected`, highlighted focus windows, a verdict badge, and an `Investigate first` summary card.
- Grafana panels do not read those checkout anomaly CSVs directly; they query API endpoints backed by `database/transactions.csv` and `database/transactions_auth_codes.csv`.

Reviewer-facing deliverables:
- start here for reviewer workflow and reproducibility: `README.md`
- presentation deck: `report/presentation.md`
- technical report: `report/technical_report.md`
- methodology reference: `docs/monitoring-methodology.md`
- architecture reference: `SYSTEM_MAP.md`
- original challenge prompt mirrored in the repo: `database/monitoring-test.md`

Optional smoke rerun after startup:

```bash
./scripts/smoke_one_click.sh
```

This smoke script verifies `/health`, authenticated happy-path access to `/metrics`, `/alerts`, and `/decision`, generated artifact presence, dashboard provisioning contract, and mock webhook delivery.
When Playwright tooling is available, smoke checks also run `./scripts/check_grafana_dashboard_playwright.sh` for reviewer-visible dashboard page/panel-title validation.
These checks validate runtime wiring and reviewer UX: API availability, authenticated endpoint wiring, generated artifacts, dashboard contract checks, and webhook delivery.
They do not, by themselves, prove unauthenticated rejection behavior across all protected endpoints or guarantee all Grafana panels are populated with data.
They do not by themselves prove the challenge 3.1 checkout conclusion in `report/presentation.md` or `report/technical_report.md`; that evidence should be reviewed directly from the datasets, SQL, generated checkout artifacts, and API outputs.

## Why Deterministic Rules Instead Of ML

This submission uses deterministic baseline-aware rules instead of a trained ML detector for the monitoring path.

- reviewer can trace every alert recommendation back to visible rates, baseline windows, floor rates, multipliers, and cooldown rules
- same input always yields the same result, which matters for challenge reproducibility and discussion under interview conditions
- the supplied dataset is finite, local, and intentionally small enough that an ML layer would add training and calibration complexity without stronger evidence quality
- local-first execution stays simple: no model training step, no feature store, no serving dependency, and no opaque scoring logic to defend
- the goal here is operational triage with auditable thresholds, not open-ended pattern discovery

Thresholds are baseline-aware rather than arbitrary constants:

- baseline window: compare the current minute bucket against the previous complete window so the system reacts to deviation from recent behavior, not only absolute rate size
- floors: each metric has a minimum rate floor so tiny historical averages do not create noisy alerts from trivial changes
- multipliers: warning and critical thresholds scale from the larger of baseline rate or floor, which preserves a consistent "how abnormal is this?" interpretation
- cooldown: repeated metric + severity alerts are suppressed for a short window so operators see state changes, not spam
- volume gates: low-traffic windows are suppressed so thresholds are only meaningful when there is enough evidence

## Security and Runtime Defaults

- Published ports are localhost-only:
  - `127.0.0.1:8000` for API
  - `127.0.0.1:3000` for Grafana
  - `127.0.0.1:8010` for the mock team receiver
- `/health` is public.
- `/monitor`, `/monitor/transaction`, `/metrics`, `/metrics/recent`, `/metrics/focus`, `/alerts`, `/decision`, `/decision/focus`, and `/decision/forecast/focus` require `X-API-Key` when `MONITORING_API_KEY` is set (enabled by default in one-click mode).
- Generated reviewer artifacts are written on host under `database/report/` and `charts/`.
- Runtime logs are written on host under `logs/`.
- Compose host mounts include `database/`, `charts/`, `grafana/`, `logs/`, and `sql/`.
- Formal alerts always write aggregate metadata to `logs/alerts.log` and, in one-click mode, also deliver a webhook payload to the local mock team receiver.

Monitoring ingestion paths:
- `POST /monitor`: aggregate minute-window replay endpoint used by the dataset, smoke tests, and dashboard-linked monitoring flow.
- `POST /monitor/transaction`: single-event endpoint that folds one transaction into its minute bucket and evaluates the resulting window through the same anomaly engine.
- `GET /metrics/recent?days=5`: compatibility endpoint for latest-anchored metrics slices.
- `GET /metrics/focus?bucket=hour|minute`: returns the newest eligible data cluster for dashboard charts; Grafana uses `bucket=hour`.
- `GET /decision/focus`: returns decision, evidence, business impact, and forecast for the selected dashboard focus cluster.
- `GET /decision/forecast/focus`: returns the focused forecast as relative-horizon rows (`+5m`, `+10m`, ...) for the "What Could Get Worse In The Forecast Window" panel.

Why both ingestion endpoints exist:

- `POST /monitor` is the canonical aggregate replay path for the provided historical dataset and deterministic smoke/bootstrap checks
- `POST /monitor/transaction` demonstrates how the same logic can be used when events arrive one at a time from an application or stream
- both paths converge on the same minute-bucket anomaly engine, so the distinction is input shape and integration style, not different alert logic
- keeping both endpoints visible makes it easier for a reviewer to verify batch replay behavior separately from near-real-time event ingestion behavior

What `transactions_auth_codes.csv` adds:

- it contributes minute-aligned auth-code distributions that sit beside the status totals in `database/transactions.csv`
- it provides triage evidence about concentration patterns inside anomalous windows, such as a dominant denial or failure reason
- it does not decide whether a window is anomalous; it explains why an already elevated window may deserve investigation first
- the API keeps the machine-readable top-code tuples and also exposes readable strings for reviewer-facing dashboard tables

What bootstrap and smoke validation proves:

- bootstrap proves the repository can generate the required first-challenge CSV/SVG artifacts before the API starts
- smoke checks prove service startup, authenticated happy-path API wiring (`/metrics`, `/alerts`, `/decision`), dashboard provisioning contract checks, mock webhook delivery, and (when tooling is present) dashboard page/panel-title rendering checks
- those checks are strong evidence that the submission runs end to end on a clean machine
- they are not a substitute for direct evidence review of the checkout conclusion, threshold reasonableness, or the meaning of a specific anomaly window

Decision guidance modes:
- Environment/config default: `DECISION_ENGINE_MODE=local` for deterministic local scoring, ranking, and forecast.
- Reviewer bootstrap default: `./scripts/reviewer_start.sh` prompts with `external` selected by default for richer reviewer-facing narrative polish, then falls back to `local` if no external key is provided.
- `DECISION_ENGINE_MODE=external`: local scoring remains authoritative; external provider may rewrite only `summary`, `top_recommendation`, `problem_explanation`, and `forecast_explanation`.
- Supported external providers: `openai`, `anthropic`, `google`.
- In interactive reviewer bootstrap mode, OpenAI external prompt defaults to `gpt-4.1-mini` unless you choose another model.
- In raw compose mode without bootstrap-selected model, defaults are `EXTERNAL_AI_PROVIDER=openai` and `EXTERNAL_AI_MODEL=gpt-4o-mini` when those variables are not set.
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

## Fallback Setup (Only If One-Click Is Not Suitable)

Compose fallback (non-interactive env file):

```bash
cp .env.example .env
docker compose up --build
```

`API_PORT` changes only the host binding (`127.0.0.1:<API_PORT>`). The internal Compose service URL stays `http://api:8000`.

Local API fallback (outside compose):

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

## Supporting References

- `docs/monitoring-methodology.md` documents the end-to-end logic, thresholds, datasets, and generated artifacts.
- `SYSTEM_MAP.md` provides a compact architecture and runtime map for the reviewer.
