## Context

The current CloudWalk monitoring service already computes anomaly severity, exposes dashboard-ready metrics, and records formal alert history. What it does not provide is a decision layer that tells an operator what matters most right now, what is likely to worsen next, and what action to take. The Grafana dashboard mirrors that gap: it shows raw metrics and recent alerts, but it does not rank priorities or separate predictive guidance from formal alert notifications.

This change crosses multiple repository surfaces:
- backend settings, models, and runtime state in `app/`
- Grafana dashboard queries and dashboard contract checks in `grafana/` and `scripts/`
- reviewer-facing docs in `README.md`, `SYSTEM_MAP.md`, `INVARIANTS.md`, and `docs/monitoring-methodology.md`

The user also wants optional AI integration, but the repository must remain usable without login, external credentials, or hosted dependencies. That means local decision logic has to remain complete and authoritative even when an external provider is enabled.

There are also two operational constraints that must stay explicit in the design:
- reviewers must be able to bring the stack up through a single guided entrypoint rather than assembling commands manually
- the optional external-provider path must not introduce secret leakage, unsafe network defaults, or ambiguous reviewer setup

## Goals / Non-Goals

**Goals:**
- Add a decision layer that ranks current transaction risks and explains the top next step.
- Add a protected `GET /decision` endpoint for dashboard consumption.
- Add short-horizon forecasting that can surface watch states before formal alert thresholds are crossed.
- Keep `/monitor`, `/metrics`, `/alerts`, and notifier behavior backward compatible.
- Allow an optional external provider to improve narrative summaries while preserving local scoring as the source of truth.
- Redesign Grafana around decision-first panels instead of raw status-only panels.
- Provide a one-step reviewer bootstrap that captures provider choice, launches the stack, validates it, and prints first-login details.
- Tighten security around API-key comparison, payload parsing, provider secrets, and reviewer-local config handling.

**Non-Goals:**
- Replacing the existing anomaly engine or formal alert thresholds.
- Introducing remote services as a hard runtime dependency.
- Building a generic AI framework with arbitrary prompts or tool use.
- Turning predictive watch states into persisted alert-history records.
- Expanding the scope to checkout-analysis dashboards in this change.

## Decisions

### Add a dedicated decision engine instead of overloading the alert engine
The current `AlertEngine` is responsible for formal alert classification from a single monitoring window. Decision guidance needs different responsibilities: ranking multiple metrics, combining recent evidence, generating short-horizon forecasts, and returning operator actions. Keeping this in a dedicated `DecisionEngine` avoids coupling dashboard guidance to `/monitor` request handling and preserves the existing alert contract.

The `DecisionEngine` will consume:
- `app.state.metrics_rows`
- `state.alert_history`
- baseline rates from the existing anomaly logic
- `auth_codes_by_timestamp` for operator clues

The engine will produce a `DecisionResponse` with:
- `generated_at`
- `overall_status` (`normal`, `watch`, `act_now`)
- `top_recommendation`
- `summary`
- `priority_items[]`
- `forecast_points[]`
- `recent_evidence[]`
- `provider_status`

Alternative considered:
- extend `AlertEngine` directly: simpler file count, but mixes formal alert semantics with dashboard-only guidance and makes future changes riskier.

### Keep local scoring authoritative and deterministic
The decision layer must work offline and without login. Local logic will therefore compute the actual priority order, risk scores, confidence, and status transitions. External AI, when enabled, may only help rewrite summary text or operator hints. It must not override severity, risk ranking, or formal alert boundaries.

Locked behavior:
- `local` mode is the default
- `external` mode is opt-in by environment variables
- external failure must fall back to local guidance without failing the endpoint
- the response must expose provider/fallback state so the dashboard can explain what happened
- only `summary` and `top_recommendation` may be externally rewritten; ranked items, statuses, scores, and alert boundaries remain local
- the supported external providers are fixed to `openai`, `anthropic`, and `google`; arbitrary base URLs are out of scope for this change
- provider status must never include API keys, raw provider responses, or request payload echoes

Alternative considered:
- external provider computes the entire decision output: rejected because it would make the system non-deterministic, login-dependent, and fragile for reviewer setup.

### Use lightweight forecast logic over recent metrics history
The system already has a small, bounded time-series dataset exposed by `metrics_rows`. A lightweight forecast is enough for this repo’s purpose: surface short-horizon risk, not deliver production-grade forecasting. The design will use a recent-window weighted moving average plus slope adjustment over the last configured lookback period.

Locked forecast behavior:
- input window comes from recent `metrics_rows`
- default lookback window is `15` minutes
- default forecast horizon is `30` minutes
- default forecast step is `5` minutes
- at least `5` history points are required before forecast output is considered valid
- weighted moving average uses weights `1..N` across the retained points
- slope is the arithmetic mean of consecutive per-minute deltas across the retained points
- forecast horizon is configurable by env
- forecast is capped to valid rate bounds
- insufficient history lowers confidence or omits forecast data
- forecasted risk may create `watch` guidance but MUST NOT create a formal alert until live anomaly thresholds are crossed

Alternative considered:
- ARIMA/ML model: too heavy and unjustified for the size and fixed nature of the dataset.

### Lock explicit decision-state mapping so implementation and tests stay aligned
The previous draft named the states but did not define the exact mapping. This must be deterministic so the endpoint, dashboard, and tests all agree.

Locked state mapping:
- `act_now` if any metric has current severity `warning` or `critical`
- `watch` if no metric is `act_now` and at least one metric is current severity `info`
- `watch` if no metric is currently `warning` or `critical`, but forecast severity reaches `info`, `warning`, or `critical` inside the configured horizon
- `normal` otherwise
- priority ordering is descending by current severity, then risk score, then forecast severity
- risk score is bounded `0..100` and must be locally computed from current severity, current-vs-baseline deviation, and forecast escalation bonus

Alternative considered:
- hand-authored state mapping in the UI: rejected because it would split logic between backend and dashboard and make tests weaker.

### Preserve formal alert boundaries and cooldown semantics
Formal alerts are already governed by `/monitor`, the anomaly engine, and the notifier. This behavior remains the authoritative path for alert history and log persistence. The new decision layer may expose current or predicted risk even when notifier output is suppressed by cooldown, but it must not backfill suppressed or forecast-only states into `alerts[*]`.

Locked semantics:
- formal alerts still require existing warning/critical threshold breaches
- `watch` is dashboard-only guidance
- cooldown still suppresses repeated notifier events
- decision guidance may continue showing elevated risk during cooldown

Alternative considered:
- writing watch states into alert history: rejected because it would blur the difference between operator guidance and formal alerts and would weaken the existing alert log meaning.

### Add a new protected `GET /decision` endpoint rather than expanding `/metrics`
`/metrics` is currently a simple historical timeseries contract. Embedding ranked decisions, summaries, and provider state into `rows[*]` would distort that API and make Grafana queries harder to reason about. A dedicated endpoint gives the dashboard one stable decision snapshot while leaving `/metrics` and `/alerts` compatible with current tests and consumers.

The endpoint will be protected by the same `build_api_key_guard()` dependency used by `/metrics` and `/alerts`.

Locked response shape:
- `generated_at`
- `overall_status`
- `top_recommendation`
- `summary`
- `priority_items[]` with metric, current severity, forecast severity, risk score, confidence, current rate, baseline rate, forecast rate, recommended action, root-cause hint, and top auth codes
- `forecast_points[]` with timestamp, metric, and forecast rate
- `recent_evidence[]` with timestamp, source, message, and top auth codes
- `provider_status` with mode, provider, model, fallback flag, and sanitized error text

Alternative considered:
- append decision fields to every metrics row: rejected because decision guidance is snapshot-oriented rather than row-oriented.

### Redesign Grafana around operator decisions, not gauges for every status
The new dashboard will prioritize panels that answer:
1. What needs attention now?
2. What is likely to worsen soon?
3. Why do we think that?
4. What should the operator check first?

Planned panel groups:
- overall status and top recommendation
- priority-ranked risk table
- forecast and current-risk trend views
- recent formal alerts
- evidence and auth-code clue table
- transaction volume context
- a reviewer-facing first-login note panel that explains Grafana credentials, API-key usage, the selected provider mode, and the distinction between predictive guidance and formal alerts

Alternative considered:
- preserve the existing raw-metric layout and only add a single decision stat: rejected because it would leave the dashboard mostly non-actionable.

### Add a reviewer bootstrap script instead of relying on raw Compose only
The repository still needs Docker Compose as the underlying runtime, but the reviewer experience should start from a single guided script. That script will collect optional provider configuration, prepare a local `.env` variant, start the containers, run smoke checks, and print the resulting access details.

Locked bootstrap behavior:
- entrypoint script lives under `scripts/`
- it copies from the committed example env file into a reviewer-local env file that remains gitignored
- reviewer-local env files are permission-restricted (owner read/write only)
- it offers `local` mode or `external` mode
- if `external` mode is chosen, it offers the provider choices `openai`, `anthropic`, and `google`, then asks for model and API key
- if no API key is provided for external mode, it falls back to local mode instead of failing half-configured
- it prints Grafana URL, Grafana admin credentials, provider mode, and the command to stop the stack
- it prints the monitoring API key only when demo defaults are active; otherwise it prints only the reviewer-local env file path/key name reference
- it runs the smoke script before declaring the environment ready

Alternative considered:
- document multiple manual steps in README only: rejected because it weakens the reviewer flow and makes provider configuration error-prone.

### Harden security-sensitive paths as part of the design
Optional provider support introduces new security footguns that the design must explicitly prevent.

Locked security decisions:
- API-key comparison remains centralized and must use constant-time comparison
- malformed `Content-Length` values on `/monitor` must fail safely rather than crash or bypass the limit
- provider API keys may be stored only in the reviewer-local env file or runtime environment, never in committed files, dashboard JSON, logs, or response payloads
- reviewer-local env files created by the bootstrap script must be gitignored and permission-restricted
- compose-published ports remain localhost-bound by default even when external providers are enabled
- provider error text surfaced in `provider_status` must be sanitized and concise

Alternative considered:
- let the reviewer edit `.env` manually for provider setup: rejected because it makes secret handling easier to get wrong and weakens the one-step reviewer contract.

## Risks / Trade-offs

- [Forecast confidence may look stronger than the underlying data supports] → Mitigation: include explicit confidence, reduce forecast output when history is thin, and document that the forecast is heuristic.
- [External AI configuration could add reviewer confusion] → Mitigation: keep local mode as the documented default and make fallback behavior explicit in response and docs.
- [A new endpoint changes dashboard contracts] → Mitigation: keep `/metrics` and `/alerts` unchanged, add targeted API and dashboard contract tests, and update smoke checks.
- [Decision summaries may duplicate alert reasons] → Mitigation: keep summary text short and derive it from ranked priority items rather than free-form duplication.
- [Dashboard complexity could grow too much] → Mitigation: constrain the first version to transaction monitoring only and keep checkout analysis out of this redesign.
- [Reviewer bootstrap could accidentally persist secrets unsafely] → Mitigation: write to a gitignored reviewer-local env file with restricted permissions and never echo raw API keys back to the terminal.
- [Provider integrations may expose unstable vendor-specific behavior] → Mitigation: keep the contract narrow, treat vendors as optional narrative rewriters only, and require deterministic local fallback.

## Migration Plan

1. Extend `Settings` and `.env.example` with decision-engine mode and forecast configuration.
2. Add decision response models and a new `DecisionEngine` implementation under `app/` using the locked state mapping and forecast rules.
3. Wire `GET /decision` into `app/main.py` with the existing API-key guard.
4. Add optional external-provider client code behind the local decision engine and fallback rules, limited to rewriting summary text only.
5. Add the reviewer bootstrap script and reviewer-local env workflow.
6. Redesign `grafana/dashboard.json` and update dashboard smoke/contract checks.
7. Update docs and invariants to describe the new endpoint, dashboard behavior, reviewer bootstrap, local-vs-external provider rules, and first-login details.
8. Add focused API and contract tests for decision guidance, fallback behavior, alert separation, bootstrap flow, and security-sensitive edge cases.

Rollback strategy:
- Remove `GET /decision`, the decision engine, and the dashboard changes.
- Existing `/monitor`, `/metrics`, `/alerts`, and alert logging remain intact, so rollback is isolated to the new decision-guidance surface.

## Open Questions

None. The change will proceed with local scoring as the default, optional external narrative augmentation only, and a guided reviewer bootstrap flow.
