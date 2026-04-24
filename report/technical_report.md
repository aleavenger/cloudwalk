# CloudWalk Monitoring Analyst Test - Technical Report

## First-Challenge Objective And Scope

Challenge 3.1 is an investigation of checkout behavior:
- compare `checkout_1.csv` and `checkout_2.csv` against a blended hourly expected baseline
- use SQL, derived anomaly CSVs, and generated charts to decide which checkout should be investigated first
- separate that prioritization from challenge 3.2, which implements the transaction monitoring runtime
- rank priority by structural interruption risk rather than total-day deviation, so multi-hour zero-gap drops outrank broad uplift

## How Data Was Processed And Evaluated

### How Checkout Behavior Was Compared Against Historical Baselines
- Input: `checkout_1.csv`, `checkout_2.csv`
- Investigation method:
  - `baseline = (same_day_last_week + avg_last_week + avg_last_month) / 3`
  - `absolute_deviation = today - baseline`
  - `relative_deviation = absolute_deviation / baseline`
  - flag material hours where `baseline >= 5`
  - classify hours as `surge`, `drop`, or `normal`, with `zero_gap` used to detect interruption windows
- Artifacts:
  - `database/report/checkout_1_anomaly.csv`
  - `database/report/checkout_2_anomaly.csv`
  - `sql/checkout_1_anomaly.sql`
  - `sql/checkout_2_anomaly.sql`
  - `charts/checkout_1.svg`
  - `charts/checkout_2.svg`
- Review flow:
  - compare today vs expected
  - inspect the strongest hourly windows in SQL and charts
  - rank which checkout deserves investigation first based on interruption risk, not just on which one moved furthest for the full day

`Expected` is a blended baseline because yesterday alone is still useful source evidence but is noisier when used by itself.

## Challenge 3.2: Runtime Monitoring And Alerting

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

## AI-Assisted Development And Human Verification

- This repository was developed as AI-assisted, human-reviewed engineering rather than a fully manual implementation.
- AI accelerated implementation, iteration, and documentation, but the final repository shape and runtime behavior were reviewed directly by a human before submission.
- Human verification checked the solution against the challenge datasets, SQL outputs, generated checkout charts, API contracts, automated tests, and end-to-end smoke validation.
- Safety-sensitive choices such as authenticated endpoints, bounded payload validation, deterministic alert logic, and sanitized logging were kept explicit in the implementation instead of delegated to opaque model behavior.

## What The Data Shows

### Which Checkout Windows Are Most Anomalous
- `checkout_2.csv` should be investigated first.
- It shows a structural anomaly: strong morning surges at `08h` and `09h`, followed by complete dropouts at `15h`, `16h`, and `17h`.
- The ranking rule is explicit: multi-hour zero-gap drops outrank a checkout that is simply above expected across the day.
- `checkout_1.csv` is secondary and should remain `watch`, not `recovering`.
- `checkout_1` has a weak morning, then elevated later windows at `10h`, `12h`, `17h`, and `22h`, so the day is still abnormal even without an outage pattern.
- This conclusion prioritizes follow-up work; it does not prove the checkout root cause by itself.

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

## Challenge Coverage

Challenge 3.1 evidence and analysis deliverables:
- analyze checkout data against a blended expected baseline
- write SQL that reproduces the anomaly comparison
- generate investigation-first charts
- explain anomaly behavior and identify which checkout should be investigated first

Challenge 3.2 runtime implementation:
- Required monitoring endpoint:
  - `POST /monitor/transaction` satisfies the “receives transaction data” path.
  - `POST /monitor` remains available for aggregate dataset replay and reproducible anomaly checks.
- Required query and real-time graphic:
  - SQL analysis lives under `sql/`.
  - Checkout anomaly CSVs and SVG charts are reviewer artifacts for the first challenge.
  - Real-time visualization for the second challenge is provided through the Grafana dashboard and the focus-scoped API flow: `/metrics/focus`, `/decision/focus`, and `/decision/forecast/focus`, with `/metrics`, `/alerts`, and `/decision` retained as broader API surfaces.
- Required anomaly model:
  - rule-based baseline-aware anomaly logic is implemented in the monitoring engine for denied, failed, and reversed rates.
- Required automatic reporting:
  - formal alerts are logged locally and, in reviewer mode, delivered to a mock team receiver through a webhook notification path.

## Which Safety Controls Protect The Monitoring Runtime

- Default local bind host: `127.0.0.1`
- Optional API key for `POST /monitor`, `POST /monitor/transaction`, `GET /metrics`, `GET /metrics/recent`, `GET /metrics/focus`, `GET /alerts`, `GET /decision`, `GET /decision/focus`, and `GET /decision/forecast/focus` via `MONITORING_API_KEY`
- Payload protections on `/monitor` and `/monitor/transaction`:
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
- The checkout investigation flags suspicious windows for follow-up, but it does not establish business or system root cause by itself.
