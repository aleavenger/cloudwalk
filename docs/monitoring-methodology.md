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
- Exposes outputs via `/monitor`, `/metrics`, `/alerts`, and `/decision`.

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

### Decision Guidance Logic (`GET /decision`)

The decision layer is built from current runtime state and does not alter formal alert generation.

Local-authoritative behavior:
- computes priority ranking across `denied`, `failed`, and `reversed`
- computes bounded risk score (`0..100`)
- computes confidence from history depth + current volume
- returns recommended action, root-cause hint, and top auth-code clues

Locked overall-status mapping:
- `act_now`: any current metric is `warning` or `critical`
- `watch`: no metric is `act_now`, but a current `info` metric or forecast-elevated metric exists
- `normal`: no current or forecasted elevated risk

Predictive separation rule:
- `watch` is guidance only and does not write new entries to `/alerts`.
- formal alert history remains tied to `/monitor` threshold breaches and cooldown rules.

### Forecast Method

Default parameters (unless overridden by env):
- lookback window: 15 minutes
- horizon: 30 minutes
- step: 5 minutes
- minimum history points: 5

Computation:
- weighted moving average over retained points with weights `1..N`
- slope from arithmetic mean of consecutive per-minute deltas
- bounded forecast rates to valid range `0.0..1.0`
- when history is insufficient, forecast output is omitted and confidence remains lower

### Optional External Narrative Mode

Default mode is local. External mode is optional and controlled by environment.

Supported providers:
- `openai`
- `anthropic`
- `google`

Safety contract:
- external provider can rewrite only `summary` and `top_recommendation`
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

## Artifact Derivation Map

From `database/*.csv`, the repository produces and exposes:

- derived checkout anomaly CSVs in `database/report/`
- checkout charts in `charts/`
- monitoring API outputs for dashboard queries
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
