## Purpose

Define the required transaction-monitoring API behavior, anomaly logic, and alerting safety controls for the monitoring service.
## Requirements
### Requirement: Monitoring endpoint SHALL return anomaly recommendations for transaction windows
The system SHALL expose an HTTP endpoint that accepts a transaction summary window and returns enough information for an operator or downstream system to decide whether the window warrants an alert.

#### Scenario: Endpoint contract fields are enforced
- **WHEN** a client sends `POST /monitor`
- **THEN** the request SHALL require `window_end` plus integer fields `approved`, `denied`, `failed`, `reversed`, `backend_reversed`, and `refunded`, and SHALL allow optional `auth_code_counts`

#### Scenario: Normal window returns no alert
- **WHEN** the monitoring endpoint receives a transaction window whose denied, failed, and reversed behavior remains within configured normal bounds
- **THEN** the response SHALL mark the recommendation as `no_alert` and include the computed rates used for that decision

#### Scenario: Abnormal window returns an alert recommendation
- **WHEN** the monitoring endpoint receives a transaction window whose denied, failed, or reversed behavior exceeds the configured anomaly criteria
- **THEN** the response SHALL mark the recommendation as `alert`, include `triggered_metrics`, include `severity`, and include both `rates` and `baseline_rates`

#### Scenario: Invalid payload is rejected
- **WHEN** the monitoring endpoint receives missing required fields or non-integer count values
- **THEN** the endpoint SHALL return HTTP `422`

#### Scenario: Oversized or unbounded payload is rejected
- **WHEN** `POST /monitor` exceeds the configured body-size or field-size safety limits
- **THEN** the endpoint SHALL reject the request with a client error status and SHALL NOT process alert logic for that payload

### Requirement: Alert decisions SHALL use baseline-aware anomaly logic
The system SHALL determine alert recommendations for denied, failed, and reversed transactions by comparing current behavior against recent historical norms while also applying minimum-volume and minimum-rate guards.

The implementation SHALL use these fixed parameters:
- baseline window: previous `60` complete minutes
- minimum total count: `80`
- minimum metric count: `3`
- floor rates: denied `0.08`, failed `0.02`, reversed `0.03`
- warning rule: `current_rate >= max(floor_rate, baseline_rate * 2.0)`
- critical rule: `current_rate >= max(floor_rate * 1.5, baseline_rate * 3.0)`
- cooldown: `10` minutes by metric + severity, with higher-severity escalation allowed

#### Scenario: Low-volume noise is suppressed
- **WHEN** a transaction window has a very small total volume or a status spike that is not meaningful in absolute terms
- **THEN** the system SHALL avoid escalating the window solely because of a misleading percentage increase

#### Scenario: Sustained deviation increases severity
- **WHEN** the same status metric remains materially above baseline across consecutive qualifying windows
- **THEN** the system SHALL assign a more severe alert outcome than it would for a mild deviation

#### Scenario: Known denied spike is alertable
- **WHEN** the model evaluates the dataset window at `2025-07-12 17:18:00` with denied count `54`
- **THEN** the system SHALL produce an `alert` recommendation with denied in `triggered_metrics`

#### Scenario: Known failed spike is alertable
- **WHEN** the model evaluates the dataset window at `2025-07-15 04:30:00` with failed count `10`
- **THEN** the system SHALL produce an `alert` recommendation with failed in `triggered_metrics`

#### Scenario: Known reversed spike is alertable
- **WHEN** the model evaluates the dataset window at `2025-07-14 06:33:00` with reversed count `7`
- **THEN** the system SHALL produce an `alert` recommendation with reversed in `triggered_metrics`

### Requirement: Monitoring service SHALL expose operational monitoring data
The system SHALL expose health, metrics, decision-guidance, and alert-history endpoints that can be consumed by reviewers and dashboard tooling.

#### Scenario: Metrics endpoint exposes dashboard-ready data
- **WHEN** a client requests monitoring metrics
- **THEN** the response SHALL return a root `rows` array containing `timestamp`, `total`, `approved_rate`, `denied_rate`, `failed_rate`, `reversed_rate`, and `alert_severity`

#### Scenario: Alert history reflects generated notifications
- **WHEN** an anomaly recommendation results in an alert event
- **THEN** the alert-history endpoint SHALL return a root `alerts` array containing the event timestamp, severity, triggering metrics, rates, baseline rates, and notification outcome

#### Scenario: Decision endpoint exposes operator guidance
- **WHEN** a client requests decision guidance
- **THEN** the response SHALL return a current decision snapshot that includes `overall_status`, `top_recommendation`, `summary`, `priority_items`, `forecast_points`, `recent_evidence`, and provider state

#### Scenario: Health endpoint is available
- **WHEN** a client requests `GET /health`
- **THEN** the endpoint SHALL return HTTP `200` with `{\"status\":\"ok\"}`

### Requirement: Monitoring endpoints SHALL enforce access control when configured
The system SHALL support API-key protection for operational endpoints so monitoring and alert data are not exposed unintentionally.

#### Scenario: Protected endpoint rejects missing key
- **WHEN** `MONITORING_API_KEY` is configured and a client calls `POST /monitor`, `GET /metrics`, `GET /alerts`, or `GET /decision` without `X-API-Key`
- **THEN** the endpoint SHALL return HTTP `401`

#### Scenario: Protected endpoint accepts valid key
- **WHEN** `MONITORING_API_KEY` is configured and the request includes a matching `X-API-Key`
- **THEN** the endpoint SHALL process the request normally

#### Scenario: Local health checks remain available
- **WHEN** a client calls `GET /health` without an API key
- **THEN** the endpoint SHALL continue returning HTTP `200`

#### Scenario: API-key validation is timing-safe
- **WHEN** a protected endpoint validates `X-API-Key`
- **THEN** the comparison SHALL be performed through the centralized guard using constant-time comparison rather than plain string equality

### Requirement: Alert logging SHALL avoid sensitive data exposure
The system SHALL log only the minimum aggregated fields needed for alert traceability and SHALL avoid persisting sensitive request material.

#### Scenario: Log output excludes secrets and raw payloads
- **WHEN** an alert event is written by the default notifier logger
- **THEN** the log entry SHALL exclude API keys, environment variables, and raw request payload bodies

### Requirement: Formal alerts SHALL remain distinct from predictive watch guidance
The system SHALL preserve existing formal alert semantics for `/monitor` and alert history while allowing the decision layer to surface predictive risk and watch states that do not emit notifier events.

#### Scenario: Warning and critical conditions remain the formal alert boundary
- **WHEN** a monitored window crosses the existing warning or critical anomaly criteria
- **THEN** the system SHALL continue to emit a formal alert recommendation and alert-history record using the existing alerting workflow

#### Scenario: Predictive watch state does not write alert history
- **WHEN** the decision layer identifies elevated or worsening risk that has not crossed a formal alert threshold
- **THEN** the system SHALL expose that state through decision guidance without appending a new record to `alerts[*]`

#### Scenario: Cooldown suppression does not hide current decision context
- **WHEN** a formal alert is suppressed by cooldown
- **THEN** the system SHALL continue to expose the current elevated state through decision guidance even if no new notification is written

### Requirement: Monitoring service SHALL fail safely on security-sensitive input paths
The system SHALL handle payload-size and provider-status edge cases without leaking secrets or crashing the reviewer-facing runtime.

#### Scenario: Malformed content-length fails safely
- **WHEN** `/monitor` receives an invalid `Content-Length` header value
- **THEN** the request SHALL fail with a client error and SHALL NOT process alert logic

#### Scenario: Provider status is sanitized
- **WHEN** the decision endpoint reports external-provider fallback
- **THEN** the surfaced provider status SHALL omit API keys, raw provider responses, and unsanitized exception text

