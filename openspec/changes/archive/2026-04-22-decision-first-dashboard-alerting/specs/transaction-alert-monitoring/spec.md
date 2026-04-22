## MODIFIED Requirements

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

## ADDED Requirements

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
