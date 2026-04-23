# SYSTEM INVARIANTS (STRICTLY ENFORCED)

These invariants define non-negotiable system rules.

Changes that violate these invariants are critical defects.

Canonical shared AI policy baseline: `RULES.md`.

---

# 1. Endpoint and Auth Contract

- `GET /health` is always public.
- `POST /monitor`, `POST /monitor/transaction`, `GET /metrics`, `GET /metrics/focus`, `GET /alerts`, `GET /decision`, `GET /decision/focus`, and `GET /decision/forecast/focus` must require `X-API-Key` if `MONITORING_API_KEY` is configured.
- API key validation must continue to be centralized in `build_api_key_guard()`.
- Unauthorized calls to protected endpoints must return HTTP 401.

---

# 2. Payload and Input Safety

- `/monitor` request payload must remain bounded by:
  - middleware body-size cap (`MAX_MONITOR_REQUEST_BYTES`)
  - per-field integer bounds (`0..1_000_000`)
  - auth-code map key count and key-length limits
- `/monitor/transaction` must remain bounded by the same middleware body-size cap and auth-code key-length validation.
- Requests exceeding configured bounds must return HTTP 422.
- `MAX_COUNT_VALUE` check in endpoint logic must remain active as hard safety validation.

---

# 3. Alert Decision Rules

- Alert severity must be derived from denied/failed/reversed rates only.
- `minimum_total_count` and `minimum_metric_count` gates must suppress low-volume noise.
- `recommendation="alert"` is allowed only for warning/critical outcomes.
- Cooldown deduplication must suppress repeated metric+severity alerts inside the configured cooldown window.

---

# 4. Metrics and Alert Response Contracts

- `MonitorResponse`, `MetricsResponse`, and `AlertsResponse` schemas in `app/models.py` are API contracts.
- `/metrics` must expose rows with: `timestamp`, `total`, `approved_rate`, `denied_rate`, `failed_rate`, `reversed_rate`, `alert_severity`.
- `/metrics/recent` must return the same row schema as `/metrics`, filtered to a latest-anchored recent-day window (`days` bounds: 1..365).
- `/metrics/focus` must return the same row schema as `/metrics`, filtered to the newest eligible focus cluster and bucketed as requested (`hour` or `minute`).
- `/alerts` entries must include `notification_status`, `team_notification_status`, `notification_channels`, `reason`, and rate/baseline snapshots.
- Auth-code tuple fields remain the canonical machine-readable representation; any readable dashboard display field must be additive and derived from those tuples.

---

# 4b. Decision Contract and Separation Rules

- `DecisionResponse` in `app/models.py` is an API contract for `GET /decision`.
- `GET /decision/focus` must return the same `DecisionResponse` schema as `/decision`, scoped to the selected dashboard-focus cluster.
- `GET /decision/forecast/focus` must return dedicated forecast chart rows scoped to the selected dashboard-focus cluster, with relative horizon labels and separate denied/failed/reversed rate fields.
- `overall_status` mapping must remain deterministic:
  - `act_now` when any current metric is `warning` or `critical`
  - `watch` when no metric is `act_now` and any metric is current `info` or forecast-elevated
  - `normal` otherwise
- `GET /decision` must include business-impact context (`business_impact` and per-priority above-normal/gap/projection fields) derived from local runtime metrics.
- `warning_gap_rate` must be computed from the same baseline-aware warning threshold definition used by formal alerting.
- `projected_excess_transactions_horizon` must use the current decision-window total as the deterministic volume proxy.
- Predictive/watch guidance must not append formal alert-history records.
- External provider integration may rewrite only `summary`, `top_recommendation`, `problem_explanation`, and `forecast_explanation`; ranking/severity/risk/business-impact numeric fields and alert boundaries remain local-authoritative.
- When `DECISION_MIN_HISTORY_POINTS=1`, `forecast_explanation` must include an explicit test/demo warning and recommend `5` as the stronger operating value.
- OpenAI external mode may target official OpenAI or an OpenAI-compatible endpoint through `EXTERNAL_AI_BASE_URL`, but the request/response contract must remain chat-completions JSON rewrite only.

---

# 5. Logging and Secret Hygiene

- `logs/alerts.log` may include only aggregated alert metadata.
- Team webhook payloads and mock-receiver captures may include only aggregated alert metadata.
- API keys and raw monitor payload bodies must never be logged.
- Auth-code distributions stored in alerts must be top-k aggregate tuples only.
- Provider status surfaced by `GET /decision` must remain sanitized and must not expose API keys, raw provider responses, or prompt/request bodies.

---

# 6. Bootstrap and Artifact Contract

- API container bootstrap must execute in this order:
  1. checkout anomaly report generation
  2. chart generation
  3. Uvicorn startup
- `docker/api-entrypoint.sh` must remain fail-fast (`set -euo pipefail`).
- One-click execution must produce:
  - `database/report/checkout_1_anomaly.csv`
  - `database/report/checkout_2_anomaly.csv`
  - `charts/checkout_1.svg`
  - `charts/checkout_2.svg`

---

# 7. Network Exposure Safety

- Compose-published ports must stay localhost-bound by default:
  - API: `127.0.0.1:${API_PORT:-8000}:8000`
  - Grafana: `127.0.0.1:${GRAFANA_PORT:-3000}:3000`
  - Mock team receiver: `127.0.0.1:${TEAM_RECEIVER_PORT:-8010}:8010`
- Default committed credentials/keys are demo-only and must be documented as local-use only.
- Local one-click Grafana mode may allow anonymous dashboard viewing (Viewer role) but must remain localhost-bound.

---

# 7b. Reviewer Bootstrap Secret Handling

- `scripts/reviewer_start.sh` is the reviewer one-step entrypoint contract.
- Bootstrap-created reviewer env file must remain gitignored (`.env.reviewer`) and permission-restricted to owner read/write.
- Bootstrap terminal output may print raw monitoring API keys only for committed demo defaults; non-demo keys must be referenced by env-file/key name only.
- Reviewer bootstrap must surface the localhost mock receiver URL and the effective team notification target.

---

# 8. Dataset and Baseline Integrity

- Runtime baseline must come from `database/transactions.csv` and `database/transactions_auth_codes.csv`.
- Missing baseline windows may fall back to global baseline means; this fallback must remain deterministic.
- Rate computation denominator must be `sum(counts.values())` and protect division by zero.

---

# 9. Methodology Documentation Invariant

- `docs/monitoring-methodology.md` must reflect current logic and artifact flow for:
  - input datasets in `database/`
  - checkout anomaly derivation
  - transaction anomaly thresholds and decision rules
  - auth-code enrichment behavior
  - generated artifacts in `database/report/`, `charts/`, and dashboard/report outputs
- `README.md` must include a reference to `docs/monitoring-methodology.md` so reviewer-facing documentation remains discoverable.

---

# 10. Grafana Provisioning Safety

- Infinity datasource URL-mode queries must only target allowlisted hosts in datasource provisioning (`allowedHosts`), including the compose API URL when one-click stack mode is used.
- Dashboard render time range must be derived from the newest eligible data cluster, not wall-clock relative time.
- Grafana metric panels must use query settings that emit typed fields (backend parser plus explicit columns) so the default provisioned dashboard renders data without manual panel edits.
- Grafana auth-code table cells must render backend-provided readable strings instead of raw JSON array serialization.
- Dashboard panel set must remain decision-first and include "What Needs Attention Right Now", "Why Each Metric Is Ranked This Way", "What Could Get Worse In The Forecast Window", "Evidence Behind The Current Recommendation", "Formal Alerts That Have Already Fired", "How Risk Rates Are Moving Over Time", "How Much Traffic These Rates Represent", and "How To Read This Dashboard On First Login".
- Dashboard panel set must include a business-impact view sourced from `GET /decision` or `GET /decision/focus`.
- Dashboard reading order must stay business-first: current priority and business impact above supporting detail, with deeper metric-ranking analysis kept below the summary/context panels.
- Grafana decision tables must render confidence/rate fields with human-readable percent units while preserving raw numeric API fields.
- Grafana must render `dashboard.json` from `dashboard.template.json`, using the newest eligible cluster window plus forecast horizon.
- Trend/volume charts must source `GET /metrics/focus?bucket=hour`, dashboard decision tables must source `GET /decision/focus`, and the forecast chart must source `GET /decision/forecast/focus`.
