# SYSTEM INVARIANTS (STRICTLY ENFORCED)

These invariants define non-negotiable system rules.

Changes that violate these invariants are critical defects.

Canonical shared AI policy baseline: `RULES.md`.

---

# 1. Endpoint and Auth Contract

- `GET /health` is always public.
- `POST /monitor`, `GET /metrics`, `GET /alerts` must require `X-API-Key` if `MONITORING_API_KEY` is configured.
- API key validation must continue to be centralized in `build_api_key_guard()`.
- Unauthorized calls to protected endpoints must return HTTP 401.

---

# 2. Payload and Input Safety

- `/monitor` request payload must remain bounded by:
  - middleware body-size cap (`MAX_MONITOR_REQUEST_BYTES`)
  - per-field integer bounds (`0..1_000_000`)
  - auth-code map key count and key-length limits
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
- `/alerts` entries must include `notification_status`, `reason`, and rate/baseline snapshots.

---

# 5. Logging and Secret Hygiene

- `logs/alerts.log` may include only aggregated alert metadata.
- API keys and raw monitor payload bodies must never be logged.
- Auth-code distributions stored in alerts must be top-k aggregate tuples only.

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
- Default committed credentials/keys are demo-only and must be documented as local-use only.

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
