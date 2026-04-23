## 1. Notification delivery and alert contracts

- [x] 1.1 Extend `app/config.py`, `.env.example`, and runtime wiring with webhook notification settings for a team-facing sink and timeout control.
- [x] 1.2 Refactor the notifier path so formal alerts write to the existing aggregated log and also attempt webhook delivery through a sanitized payload.
- [x] 1.3 Extend alert-history models and API responses with additive team notification fields that distinguish legacy local reporting from actual team-delivery outcome.
- [x] 1.4 Ensure webhook-disabled and webhook-failure cases are represented honestly in alert history without crashing the monitoring runtime.

## 2. Monitoring ingestion behavior

- [x] 2.1 Add a `POST /monitor/transaction` request model and protected endpoint that accepts a single transaction event with timestamp, status, and optional auth code.
- [x] 2.2 Normalize transaction events into minute buckets, update runtime counts/auth-code tallies, and reuse the existing anomaly engine plus formal alert workflow.
- [x] 2.3 Keep `POST /monitor` backward compatible for aggregate dataset replay and ensure both ingestion paths produce the same `MonitorResponse` contract.
- [x] 2.4 Preserve access-control, payload-safety, and secret-hygiene behavior across both monitoring endpoints.

## 3. Reviewer runtime and one-click validation

- [x] 3.1 Add a lightweight local mock notification receiver service to the Docker Compose reviewer stack with localhost-only exposure.
- [x] 3.2 Wire the API service to use the local mock receiver as the default webhook target in one-click mode while allowing external override via environment configuration.
- [x] 3.3 Update `scripts/reviewer_start.sh` to surface the mock receiver in reviewer messaging and keep demo credentials/local-safe behavior intact.
- [x] 3.4 Extend `scripts/smoke_one_click.sh` to trigger a known alert and verify that the mock receiver recorded the expected team-notification payload.

## 4. Documentation and verification

- [x] 4.1 Update `README.md`, `report/technical_report.md`, `SYSTEM_MAP.md`, `INVARIANTS.md`, and `docs/monitoring-methodology.md` so they accurately describe webhook delivery, one-click provisioning, and the two monitoring ingestion paths.
- [x] 4.2 Add or update API tests for webhook success/failure/disabled outcomes, new alert-history fields, and `POST /monitor/transaction` minute-bucket aggregation behavior.
- [x] 4.3 Add or update reviewer-runtime validation for the local mock receiver, compose defaults, and smoke-check notification verification.
- [x] 4.4 Run the targeted test suite, dashboard/runtime contract checks, and a Playwright-backed UI verification if Playwright tooling is available in the environment.
