# CloudWalk Monitoring Analyst Test - Technical Report

## What This Monitoring Workflow Delivers

Build a lightweight monitoring workflow that:
- detects anomalous checkout and transaction behavior,
- explains anomalies with SQL and chart evidence,
- returns actionable alert recommendations through an API,
- reports formal alerts automatically to a team-facing notification target,
- supports dashboard visualization and local-safe operational controls.

## How Data Was Processed And Evaluated

### How Checkout Behavior Was Compared Against Historical Baselines
- Input: `checkout_1.csv`, `checkout_2.csv`
- SQL baseline:
  - `baseline = (same_day_last_week + avg_last_week + avg_last_month) / 3`
  - `absolute_deviation = today - baseline`
  - `relative_deviation = absolute_deviation / baseline`
- Artifacts:
  - `sql/checkout_1_anomaly.sql`
  - `sql/checkout_2_anomaly.sql`
  - `charts/checkout_1.svg`
  - `charts/checkout_2.svg`

### How Transaction Windows Were Evaluated For Alert Risk
- Input: `transactions.csv`, `transactions_auth_codes.csv`
- Ingestion paths:
  - `POST /monitor` for aggregate minute-window replay
  - `POST /monitor/transaction` for single transaction events folded into minute buckets
- Minute-level rates computed for denied/failed/reversed.
- Hybrid anomaly rules:
  - baseline window: use the previous 60 complete minutes to represent current normal behavior.
  - minimum total count: require at least 80 transactions in the minute before a spike is treated as meaningful.
  - minimum metric count: require at least 3 denied, failed, or reversed events before that metric can drive an alert.
  - warning threshold: trigger warning when current rate reaches `max(floor_rate, baseline * 2.0)`, so low baselines do not cause noisy alerts.
  - critical threshold: trigger critical when current rate reaches `max(floor_rate * 1.5, baseline * 3.0)`, so severe sustained drift is escalated.
  - cooldown: suppress repeated alerts for 10 minutes per metric + severity pair to avoid duplicate team noise.
- Decision/business-impact guidance:
  - `above_normal_rate = max(0, current_rate - baseline_rate)`
  - `forecast_above_normal_rate = max(0, forecast_rate - baseline_rate)`
  - `warning_gap_rate = max(0, warning_threshold - current_rate)` with warning threshold aligned to formal alerting logic
  - `excess_transactions_now = round(above_normal_rate * total)`
  - `projected_excess_transactions_horizon = round(forecast_above_normal_rate * total)` using current-window volume as deterministic projection proxy

## What The Data Shows

### Which Checkout Windows Are Most Anomalous
- `checkout_2.csv` is the stronger anomaly case.
- Major morning surge at `08h` and `09h` where `today` is materially above historical references.
- `checkout_1.csv` shows elevated but milder windows, notably around `10h`, `12h`, `15h`, and `17h`.

### Which Transaction Minutes Triggered Formal Alerts
- Denied spike: the minute ending `2025-07-12 17:18:00` had 54 denied transactions, pushing denied behavior above the configured normal range and triggering a formal alert.
- Failed spike: the minute ending `2025-07-15 04:30:00` had 10 failed transactions, crossing the failed-rate threshold and triggering a formal alert.
- Reversed spike: the minute ending `2025-07-14 06:33:00` had 7 reversed transactions, crossing the reversed-rate threshold and triggering a formal alert.

### Which Authorization Codes Explain Spikes
- Dominant `00` authorization volume tracks approvals.
- Non-`00` codes (notably `59` and `51`) are useful drilldown context during denied spikes.
- Auth-code top-k is attached to alert records and webhook payloads as aggregate-only metadata.

### How Formal Alerts Are Reported To Teams
- Formal alerts always write aggregate metadata to `logs/alerts.log`.
- In one-click reviewer mode, formal alerts also post the same aggregate payload to a local mock team receiver through a webhook contract.
- Webhook delivery status is surfaced separately from the legacy local reporting field so reviewer-visible alert history does not overclaim team delivery.

### How The Decision Layer Explains Business Impact
- `/decision` now includes `problem_explanation` and `forecast_explanation` to separate current issue interpretation from near-term forecast interpretation.
- `/decision` also includes a `business_impact` object with top metric, likely owner/domain, above-normal delta, warning-gap distance, and excess affected transaction estimates.
- Optional external provider mode can rewrite only narrative fields (`summary`, `top_recommendation`, `problem_explanation`, `forecast_explanation`); all ranking/risk/threshold/business-impact numerics remain locally authoritative.

## How This Repository Satisfies The Challenge Requirements

- Required monitoring endpoint:
  - `POST /monitor/transaction` satisfies the “receives transaction data” path.
  - `POST /monitor` remains available for aggregate dataset replay and reproducible anomaly checks.
- Required query and real-time graphic:
  - SQL analysis lives under `sql/`.
  - Real-time visualization is provided through the Grafana dashboard and `/metrics`, `/alerts`, and `/decision` API outputs.
- Required anomaly model:
  - rule-based baseline-aware anomaly logic is implemented in the monitoring engine for denied, failed, and reversed rates.
- Required automatic reporting:
  - formal alerts are logged locally and, in reviewer mode, delivered to a mock team receiver through a webhook notification path.

## Which Safety Controls Protect The Monitoring Runtime

- Default local bind host: `127.0.0.1`
- Optional API key for `/monitor`, `/monitor/transaction`, `/metrics`, `/alerts`, and `/decision` via `MONITORING_API_KEY`
- Payload protections on `/monitor`:
  - max body size: 64 KB, which bounds request payload size before anomaly logic executes.
  - max count value: 1,000,000 per count field, preventing unrealistic spikes from malformed payloads.
  - max auth code keys: 32, limiting auth-code cardinality per request.
  - max auth code key length: 16 characters, preventing oversized or unsafe auth-code keys.
- Logging hygiene:
  - only aggregated alert metadata is logged
  - no raw request payloads
  - no API keys or environment values

## Known Limits Of This Local Demonstration

- Local in-memory state (alerts and cooldown) is process-scoped.
- One-click reviewer mode provisions the Grafana plugin and a localhost mock team receiver automatically; manual local mode still requires a manual Grafana install path and an optional webhook target if team delivery is being tested outside compose.
- Dataset is historical snapshot, so real-time behavior is replay-like for demonstration.
