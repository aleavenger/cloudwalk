## Why

The current submission passes its internal tests, but it still leaves three challenge-compliance gaps open: notifications are only written to a local log instead of being delivered to a team-facing sink, the primary monitoring endpoint accepts aggregate windows rather than individual transaction events, and the reviewer-facing report/docs do not fully match the runtime behavior. These gaps are visible against `database/monitoring-test.md` and should be closed now so the repository aligns with both the prompt and the running system.

## What Changes

- Add a real team-notification path using a webhook notifier while keeping local log output for traceability.
- Provision a local mock team receiver in the one-click reviewer stack so notifications can be demonstrated end to end without external services.
- Add a transaction-event monitoring endpoint that accepts single transaction events, folds them into minute buckets, and reuses the existing anomaly engine.
- Keep the existing aggregate `POST /monitor` endpoint for dataset replay, dashboard compatibility, and current tests.
- Extend alert-history output so reviewer-visible notification status reflects actual team-delivery outcome rather than only local file logging.
- Update reviewer startup, smoke checks, and documentation so the report and runtime explicitly map back to the challenge requirements.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `transaction-alert-monitoring`: Extend the monitoring contract with transaction-event ingestion, truthful team-notification delivery state, and webhook-based automatic reporting.
- `monitoring-visualization-and-reporting`: Update the reviewer-facing report and deliverable expectations so documentation accurately describes the runtime, notification behavior, and prompt coverage.
- `reviewer-one-click-runtime`: Extend the one-click stack to include a local mock team receiver and smoke validation for end-to-end notification delivery.

## Impact

- Backend runtime in `app/` for notifier behavior, settings, models, and a new additive endpoint.
- Reviewer stack and validation flow in `docker-compose.yml`, `.env.example`, and `scripts/`.
- Documentation and report alignment in `README.md`, `report/technical_report.md`, `SYSTEM_MAP.md`, `INVARIANTS.md`, and `docs/monitoring-methodology.md`.
- OpenSpec delta specs and implementation tasks covering prompt compliance rather than new product scope.
