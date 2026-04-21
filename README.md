# CloudWalk Monitoring Test Submission

This repository implements the CloudWalk monitoring analyst challenge with:
- checkout anomaly analysis (SQL + charts + findings),
- a FastAPI transaction monitoring service with alert recommendations,
- Grafana dashboard visualization,
- local-safe defaults for reviewer execution.

## One-Click Reviewer Setup (Primary)

Prerequisites:
- Docker Engine
- Docker Compose (v2, `docker compose`)
- Network access to pull images and the pinned Grafana Infinity plugin

Single command startup:

```bash
docker compose up --build
```

Services:
- API: `http://127.0.0.1:8000`
- Grafana: `http://127.0.0.1:3000`

Default demo credentials:
- Grafana user: `admin`
- Grafana password: `admin`
- API key header: `X-API-Key: reviewer-local-demo-key`

Demo key notice:
- `reviewer-local-demo-key` is a local demo value only.
- It is intentionally committed for evaluator convenience and is safe only because ports are bound to `127.0.0.1`.

The stack automatically:
- generates `database/report/checkout_1_anomaly.csv` and `database/report/checkout_2_anomaly.csv`,
- generates `charts/checkout_1.svg` and `charts/checkout_2.svg`,
- provisions Grafana datasource and dashboard from `grafana/dashboard.json`.

Smoke checks after startup:

```bash
./scripts/smoke_one_click.sh
```

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
- `/health` is public.
- `/monitor`, `/metrics`, and `/alerts` require `X-API-Key` when `MONITORING_API_KEY` is set (enabled by default in one-click mode).
- Output directories are mounted to host:
  - `report/`
  - `charts/`
  - `logs/`

## Grafana URL Distinction

- One-click compose mode uses internal container URL: `http://api:8000`.
- Manual/local-host mode (outside compose) should use `http://127.0.0.1:8000`.

The provisioned dashboard is optimized for compose mode and expects the internal API URL.

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
