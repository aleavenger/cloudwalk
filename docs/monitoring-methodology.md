# Monitoring Methodology

This document explains the logic used to produce the submission results end to end. It is the source-of-truth explanation of how raw datasets become anomaly outputs, charts, API metrics, dashboard views, and report conclusions.

## Inputs and Canonical Data Paths

The implementation uses the following canonical inputs under `database/`:

- `database/checkout_1.csv`
- `database/checkout_2.csv`
- `database/transactions.csv`
- `database/transactions_auth_codes.csv`

Derived checkout anomaly tables are written to:

- `database/report/checkout_1_anomaly.csv`
- `database/report/checkout_2_anomaly.csv`

## Result-Generation Flow

The system has two analysis tracks and one reviewer-facing presentation layer.

1. Checkout anomaly track
- Reads the two checkout datasets.
- Computes a per-hour baseline.
- Computes absolute and relative deviation against that baseline.
- Writes derived anomaly CSVs.
- Generates checkout comparison charts in `charts/`.

2. Transaction monitoring track
- Reads minute-level status totals from `database/transactions.csv`.
- Reads minute-level auth-code totals from `database/transactions_auth_codes.csv`.
- Computes baseline-aware anomaly decisions for denied/failed/reversed behavior.
- Exposes outputs via aggregate replay (`/monitor`), single-event ingestion (`/monitor/transaction`), `/metrics`, `/alerts`, and `/decision`.
- Reports formal alerts through the local aggregate log and, when configured, a team-facing webhook target.

3. Presentation and conclusions
- Charts in `charts/`.
- Dashboard assets in `grafana/`.
- Narrative conclusions and methodology context in `report/technical_report.md`.

## Checkout Analysis Logic

For each hour in `checkout_1.csv` and `checkout_2.csv`, checkout analysis computes:

- `baseline = (same_day_last_week + avg_last_week + avg_last_month) / 3`
- `absolute_deviation = today - baseline`
- `relative_deviation = absolute_deviation / baseline` (when baseline is non-zero)

This preserves source columns and adds reproducible anomaly indicators.

### Why the highlighted windows were chosen

The highlighted windows are chosen for material deviation versus baseline with enough operational relevance to avoid overemphasizing low-volume noise.

- `checkout_2` morning surge (`08h`/`09h`) is the strongest checkout anomaly pattern.
- `checkout_1` has elevated but milder windows (for example `10h`, `12h`, `15h`, `17h`).

## Transaction Monitoring Logic

The monitoring logic is baseline-aware and deterministic for the same input.

Fixed parameters:

- baseline window: previous `60` complete minutes
- minimum total count: `80`
- minimum metric count: `3`
- floor rates: denied `0.08`, failed `0.02`, reversed `0.03`
- warning multiplier: `2.0`
- critical multiplier: `3.0`
- cooldown: `10` minutes by metric + severity (with escalation behavior allowed)

Alert recommendation behavior:

- return `no_alert` when metrics are normal or suppressed by low-volume gates
- return `alert` when rate behavior materially exceeds threshold conditions
- deduplicate repeated equivalent alert conditions during cooldown windows

Ingestion modes:

- `POST /monitor` accepts a pre-aggregated minute window and is the primary dataset replay path.
- `POST /monitor/transaction` accepts a single transaction event (`timestamp`, `status`, optional `auth_code`), normalizes it to a minute bucket, and evaluates the accumulated bucket through the same anomaly engine.

### Decision Guidance Logic (`GET /decision`)

The decision layer is built from current runtime state and does not alter formal alert generation.

Local-authoritative behavior:
- computes priority ranking across `denied`, `failed`, and `reversed`
- computes bounded risk score (`0..100`)
- computes confidence from history depth + current volume
- computes deterministic business-impact fields (`above_normal_rate`, `forecast_above_normal_rate`, `warning_gap_rate`, excess-transaction projections)
- returns recommended action, root-cause hint, and top auth-code clues

Locked overall-status mapping:
- `act_now`: any current metric is `warning` or `critical`
- `watch`: no metric is `act_now`, but a current `info` metric or forecast-elevated metric exists
- `normal`: no current or forecasted elevated risk

Predictive separation rule:
- `watch` is guidance only and does not write new entries to `/alerts`.
- formal alert history remains tied to `/monitor` threshold breaches and cooldown rules.

Business-impact derivation:
- `above_normal_rate = max(0, current_rate - baseline_rate)`
- `forecast_above_normal_rate = max(0, forecast_rate - baseline_rate)` when forecast exists
- `warning_gap_rate = max(0, warning_threshold - current_rate)` using the same warning-threshold formula as formal alerting
- `excess_transactions_now = round(above_normal_rate * total)`
- `projected_excess_transactions_horizon = round(forecast_above_normal_rate * total)` using current window volume as deterministic proxy
- metric ownership mapping:
  - denied -> customer payment friction / issuer-acquirer ops
  - failed -> processing reliability / platform-gateway engineering
  - reversed -> reconciliation integrity / finance-reconciliation ops

### Forecast Method

Default parameters (unless overridden by env):
- lookback window: 15 minutes
- horizon: 30 minutes
- step: 5 minutes
- minimum history points: 1 (demo default; recommended production value is 5)

Computation:
- weighted moving average over retained points with weights `1..N`
- slope from arithmetic mean of consecutive per-minute deltas
- bounded forecast rates to valid range `0.0..1.0`
- when history is insufficient, forecast output is omitted and confidence remains lower
- when minimum history points is set to 1, forecast text includes a warning that this is test/demo-only and recommends 5

### Dashboard Recent-Focus Window

- Focus selection sorts timestamps, splits clusters on gaps greater than `90 minutes`, and prefers the newest cluster with at least `5` points; if none are eligible, it falls back to the newest cluster.
- `GET /metrics/focus?bucket=hour|minute` returns the same metrics schema as `/metrics`, but filtered to the selected focus cluster and optionally aggregated to hourly buckets.
- `GET /decision/focus` returns the same decision schema as `/decision`, scoped to the selected focus cluster so forecast/evidence align with the dashboard time window.
- `GET /decision/forecast/focus` reshapes the focused forecast into relative-horizon rows with `minutes_ahead`, `horizon_label`, per-metric forecast rates, and `max_rate` for panel-friendly visualization.
- Grafana renders `dashboard.json` from `dashboard.template.json` using the selected cluster start and an end time extended through the forecast horizon.
- The `What Could Get Worse In The Forecast Window` panel intentionally does not use the dashboard-wide absolute time axis; it renders the same focused forecast against adaptive relative horizon labels such as `+5m`, `+10m`, and `+15m`.
- `GET /metrics/recent?days=N` remains available as a compatibility endpoint for latest-anchored slicing outside the dashboard flow.

### Optional External Narrative Mode

Default mode is local. External mode is optional and controlled by environment.

Supported providers:
- `openai`
- `anthropic`
- `google`
- `openai` may optionally use an OpenAI-compatible endpoint via `EXTERNAL_AI_BASE_URL` (empty keeps official OpenAI)

Safety contract:
- external provider can rewrite only `summary`, `top_recommendation`, `problem_explanation`, and `forecast_explanation`
- local logic remains authoritative for status/ranking/severity/risk
- failure, timeout, or invalid external output falls back to local guidance
- surfaced provider status is sanitized and excludes API keys/raw payloads

Known spike anchors used for acceptance:

- denied spike: `2025-07-12 17:18:00`
- failed spike: `2025-07-15 04:30:00`
- reversed spike: `2025-07-14 06:33:00`

## Auth-Code Enrichment Logic

Auth-code data is used as triage context for anomalous windows:

- map auth-code counts to the same transaction timestamps
- surface leading auth codes for alertable windows
- help distinguish concentrated failure patterns from distributed ones
- keep tuple-based top-code fields as the canonical machine-readable contract
- derive readable dashboard strings (for example `51 Insufficient funds x6`) from the same top-code tuples

Auth codes enrich anomaly explanation but do not replace status-based anomaly detection.

## Automatic Reporting Logic

Formal alerts use a dual reporting path:

- always write aggregate metadata to `logs/alerts.log`
- optionally deliver the same aggregate payload to a configured webhook target

In the one-click reviewer runtime, the webhook target defaults to a localhost mock team receiver so reviewers can validate end-to-end delivery without external services.

## Artifact Derivation Map

From `database/*.csv`, the repository produces and exposes:

- derived checkout anomaly CSVs in `database/report/`
- checkout charts in `charts/`
- monitoring API outputs for dashboard queries
- mock team notification captures in `logs/` during one-click runtime
- dashboard visualization configuration in `grafana/`
- written conclusions in `report/technical_report.md`

## Limitations and Assumptions

- This is a reviewer-focused local submission, not a production risk platform.
- Thresholds are intentionally fixed for deterministic reproducibility.
- Conclusions are bounded by the provided datasets and windows.
- Local demo credentials and localhost-only exposure are part of the reviewer workflow, not production guidance.
- Forecast guidance is heuristic and intended for short-horizon operator prioritization, not long-term prediction.

## When to Update This File

Update this file whenever any of the following change:

- anomaly logic, threshold parameters, or cooldown behavior
- canonical dataset paths or data layout under `database/`
- generated artifact locations/names (`database/report/`, `charts/`, dashboard contracts)
- reasoning behind highlighted anomaly windows or report conclusions
- auth-code enrichment behavior

If this file changes in a way that affects reviewer guidance or discoverability, update `README.md` in the same change.
