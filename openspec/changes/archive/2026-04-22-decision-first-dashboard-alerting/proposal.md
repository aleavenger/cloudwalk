## Why

The current dashboard exposes raw monitoring data, but it does not help an operator decide what needs attention first, what is likely to worsen, or what action to take next. This change adds a decision-oriented layer so the system can surface priorities, short-term risk, and investigation guidance without weakening the existing alert safety rules.

## What Changes

- Add a decision-guidance capability that ranks current transaction risks, generates short-horizon forecasts, and produces operator-facing recommendations.
- Add a new protected `GET /decision` endpoint that returns current status, priority items, recent evidence, and provider/fallback state.
- Allow the decision layer to run in local mode by default and optional external-AI augmentation mode through `.env` and runtime settings.
- Redesign the Grafana dashboard around operator decisions: top recommendation, current priority queue, forecast risk, causal evidence, and formal alert history.
- Add a one-step reviewer bootstrap flow that starts the stack, validates it, and clearly presents provider-mode choices, demo credentials, and first-login guidance.
- Clarify the relationship between formal alerts and dashboard guidance so predictive `watch`/forecast states can be shown without changing the existing notifier contract.
- Tighten security-sensitive behavior around API-key validation, payload handling, provider-key usage, and reviewer-local secret storage so the optional AI path does not weaken the local-safe reviewer contract.

## Capabilities

### New Capabilities
- `decision-guidance`: Compute operator-facing priority, forecast, confidence, and recommended actions from monitoring metrics and recent alert evidence.

### Modified Capabilities
- `transaction-alert-monitoring`: Extend the monitoring service contract to expose decision guidance alongside existing alerting behavior while preserving the formal `/monitor`, `/metrics`, and `/alerts` rules.
- `monitoring-visualization-and-reporting`: Change the reviewer-facing dashboard requirements from raw metric display to decision-first monitoring views and predictive risk presentation.
- `reviewer-one-click-runtime`: Extend the reviewer startup flow from a bare Compose command to a guided one-step bootstrap that sets provider mode, starts containers, runs smoke checks, and prints reviewer access details.

## Impact

- Backend code in `app/` for settings, models, runtime state, and a new decision engine.
- Grafana assets in `grafana/` plus dashboard contract tests and smoke checks.
- A new reviewer bootstrap script under `scripts/` that writes local reviewer config, launches Compose, and reports the resulting access details.
- Documentation in `README.md`, `SYSTEM_MAP.md`, `INVARIANTS.md`, and `docs/monitoring-methodology.md`.
- Optional external AI provider integration controlled by environment configuration, with local fallback remaining the default behavior.
