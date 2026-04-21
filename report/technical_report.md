# CloudWalk Monitoring Analyst Test - Technical Report

## Objective

Build a lightweight monitoring workflow that:
- detects anomalous checkout and transaction behavior,
- explains anomalies with SQL and chart evidence,
- returns actionable alert recommendations through an API,
- supports dashboard visualization and local-safe operational controls.

## Methodology

### Checkout analysis
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

### Transaction monitoring
- Input: `transactions.csv`, `transactions_auth_codes.csv`
- Minute-level rates computed for denied/failed/reversed.
- Hybrid anomaly rules:
  - baseline: previous 60 complete minutes
  - minimum total count: 80
  - minimum metric count: 3
  - warning threshold: `max(floor_rate, baseline * 2.0)`
  - critical threshold: `max(floor_rate * 1.5, baseline * 3.0)`
  - cooldown: 10 minutes by metric + severity

## Findings

### Checkout anomalies
- `checkout_2.csv` is the stronger anomaly case.
- Major morning surge at `08h` and `09h` where `today` is materially above historical references.
- `checkout_1.csv` shows elevated but milder windows, notably around `10h`, `12h`, `15h`, and `17h`.

### Transaction anomaly examples
- Denied spike: `2025-07-12 17:18:00` (denied count 54) triggers alert.
- Failed spike: `2025-07-15 04:30:00` (failed count 10) triggers alert.
- Reversed spike: `2025-07-14 06:33:00` (reversed count 7) triggers alert.

### Auth-code triage context
- Dominant `00` authorization volume tracks approvals.
- Non-`00` codes (notably `59` and `51`) are useful drilldown context during denied spikes.
- Auth-code top-k is attached to alert records when provided in endpoint payload.

## Security Controls

- Default local bind host: `127.0.0.1`
- Optional API key for `/monitor`, `/metrics`, `/alerts` via `MONITORING_API_KEY`
- Payload protections on `/monitor`:
  - max body size: 64 KB
  - max count value: 1,000,000
  - max auth code keys: 32
  - max auth code key length: 16
- Logging hygiene:
  - only aggregated alert metadata is logged
  - no raw request payloads
  - no API keys or environment values

## Limitations

- Local in-memory state (alerts and cooldown) is process-scoped.
- Dashboard targets local API and requires manual Grafana plugin setup.
- Dataset is historical snapshot, so real-time behavior is replay-like for demonstration.
