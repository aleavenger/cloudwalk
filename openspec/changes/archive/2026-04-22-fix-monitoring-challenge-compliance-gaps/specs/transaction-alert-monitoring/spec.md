## MODIFIED Requirements

### Requirement: Monitoring endpoint SHALL return anomaly recommendations for transaction windows
The system SHALL expose an HTTP endpoint that accepts a transaction summary window and returns enough information for an operator or downstream system to decide whether the window warrants an alert.

The system SHALL also expose an additive transaction-event endpoint that accepts a single transaction event, folds it into the corresponding minute bucket, and evaluates that bucket through the same anomaly engine and alert workflow.

#### Scenario: Aggregate endpoint contract fields are enforced
- **WHEN** a client sends `POST /monitor`
- **THEN** the request SHALL require `window_end` plus integer fields `approved`, `denied`, `failed`, `reversed`, `backend_reversed`, and `refunded`, and SHALL allow optional `auth_code_counts`

#### Scenario: Transaction-event endpoint contract fields are enforced
- **WHEN** a client sends `POST /monitor/transaction`
- **THEN** the request SHALL require `timestamp` and `status`, SHALL allow optional `auth_code`, and SHALL reject unsupported status values with a client error

#### Scenario: Transaction events accumulate into minute windows
- **WHEN** the transaction-event endpoint receives multiple events in the same minute
- **THEN** the system SHALL aggregate them into the same minute bucket before evaluating anomaly logic and returning the resulting recommendation for that bucket

#### Scenario: Normal window returns no alert
- **WHEN** either monitoring endpoint evaluates a transaction window whose denied, failed, and reversed behavior remains within configured normal bounds
- **THEN** the response SHALL mark the recommendation as `no_alert` and include the computed rates used for that decision

#### Scenario: Abnormal window returns an alert recommendation
- **WHEN** either monitoring endpoint evaluates a transaction window whose denied, failed, or reversed behavior exceeds the configured anomaly criteria
- **THEN** the response SHALL mark the recommendation as `alert`, include `triggered_metrics`, include `severity`, and include both `rates` and `baseline_rates`

#### Scenario: Invalid payload is rejected
- **WHEN** a monitoring endpoint receives missing required fields or invalid field types
- **THEN** the endpoint SHALL return HTTP `422`

#### Scenario: Oversized or unbounded aggregate payload is rejected
- **WHEN** `POST /monitor` exceeds the configured body-size or field-size safety limits
- **THEN** the endpoint SHALL reject the request with a client error status and SHALL NOT process alert logic for that payload

### Requirement: Monitoring service SHALL expose operational monitoring data
The system SHALL expose health, metrics, decision-guidance, and alert-history endpoints that can be consumed by reviewers and dashboard tooling.

#### Scenario: Metrics endpoint exposes dashboard-ready data
- **WHEN** a client requests monitoring metrics
- **THEN** the response SHALL return a root `rows` array containing `timestamp`, `total`, `approved_rate`, `denied_rate`, `failed_rate`, `reversed_rate`, and `alert_severity`

#### Scenario: Alert history reflects generated notifications
- **WHEN** an anomaly recommendation results in an alert event
- **THEN** the alert-history endpoint SHALL return a root `alerts` array containing the event timestamp, severity, triggering metrics, rates, baseline rates, the legacy notification outcome field, team notification status, and the channels used for reporting

#### Scenario: Decision endpoint exposes operator guidance
- **WHEN** a client requests decision guidance
- **THEN** the response SHALL return a current decision snapshot that includes `overall_status`, `top_recommendation`, `summary`, `priority_items`, `forecast_points`, `recent_evidence`, and provider state

#### Scenario: Health endpoint is available
- **WHEN** a client requests `GET /health`
- **THEN** the endpoint SHALL return HTTP `200` with `{\"status\":\"ok\"}`

### Requirement: Monitoring endpoints SHALL enforce access control when configured
The system SHALL support API-key protection for operational endpoints so monitoring and alert data are not exposed unintentionally.

#### Scenario: Protected endpoint rejects missing key
- **WHEN** `MONITORING_API_KEY` is configured and a client calls `POST /monitor`, `POST /monitor/transaction`, `GET /metrics`, `GET /alerts`, or `GET /decision` without `X-API-Key`
- **THEN** the endpoint SHALL return HTTP `401`

#### Scenario: Protected endpoint accepts valid key
- **WHEN** `MONITORING_API_KEY` is configured and the request includes a matching `X-API-Key`
- **THEN** the protected endpoint SHALL process the request normally

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

#### Scenario: Team notification payload excludes secrets and raw payloads
- **WHEN** a formal alert is delivered through the team-notification sink
- **THEN** the outbound payload SHALL include only aggregated alert metadata and SHALL exclude API keys, raw request bodies, and other secret-bearing configuration values

## ADDED Requirements

### Requirement: Formal alerts SHALL deliver to a team-facing notification sink
The system SHALL report formal alert events automatically through a team-facing webhook sink while retaining local aggregated log output for reviewer traceability.

#### Scenario: Formal alert sends webhook notification when configured
- **WHEN** a formal alert is generated and a team webhook URL is configured
- **THEN** the system SHALL attempt webhook delivery and record the team notification outcome in alert history

#### Scenario: Demo runtime includes a local team notification receiver
- **WHEN** the reviewer one-click stack starts with its default local configuration
- **THEN** the monitoring service SHALL target a local mock team receiver so end-to-end notification delivery can be demonstrated without external services

#### Scenario: Webhook delivery failure does not drop alert history
- **WHEN** webhook delivery fails or times out
- **THEN** the system SHALL still retain the formal alert record, mark team notification as failed, and continue serving monitoring APIs without crashing

#### Scenario: Disabled webhook is represented honestly
- **WHEN** team webhook delivery is not configured outside the demo runtime
- **THEN** the system SHALL keep local alert traceability and mark the team notification status as disabled rather than claiming delivery succeeded
