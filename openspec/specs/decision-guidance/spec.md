# decision-guidance Specification

## Purpose
TBD - created by archiving change decision-first-dashboard-alerting. Update Purpose after archive.
## Requirements
### Requirement: Decision guidance SHALL rank current transaction risks
The system SHALL derive operator-facing decision guidance from recent monitoring metrics, alert history, baseline rates, and authorization-code context so the highest-priority issue is visible without manual correlation and understandable in business terms.

#### Scenario: Highest-risk metric is ranked first with business-impact context
- **WHEN** recent monitoring windows show more than one elevated metric
- **THEN** the decision output SHALL return a priority-ordered list that places the highest-risk metric first and includes severity, risk score, current rate, baseline rate, `above_normal_rate`, `forecast_above_normal_rate`, `excess_transactions_now`, `projected_excess_transactions_horizon`, and `warning_gap_rate` for each listed item

#### Scenario: Overall status mapping is deterministic
- **WHEN** decision guidance evaluates the latest monitoring state
- **THEN** it SHALL map status to `act_now` when any metric is currently `warning` or `critical`, to `watch` when no metric is `act_now` but at least one metric is current `info` or forecast-elevated, and to `normal` otherwise

#### Scenario: Guidance includes an actionable next step and likely owner
- **WHEN** the decision output identifies a priority item
- **THEN** the system SHALL include a recommended operator action, a root-cause hint, a domain label, and a likely owner for that item

#### Scenario: Problem explanation clarifies why a metric is elevated without overclaiming an alert
- **WHEN** the top metric is above baseline but remains below the formal warning threshold
- **THEN** the decision output SHALL explain that the metric is above normal, describe the business meaning of that deviation, and state that the window has not yet crossed the formal alert boundary

#### Scenario: Low-confidence windows remain visible without overclaiming
- **WHEN** the available evidence is too thin to support a strong conclusion
- **THEN** the decision output SHALL include the item with reduced confidence rather than presenting an unsupported definitive explanation

### Requirement: Decision guidance SHALL provide short-horizon risk forecasting
The system SHALL estimate near-term deterioration risk from recent monitoring history so the dashboard can surface windows that are likely to breach formal alert thresholds soon.

The implementation SHALL use these fixed defaults unless overridden by configuration:
- lookback window: `15` minutes
- forecast horizon: `30` minutes
- forecast step: `5` minutes
- minimum history points: `5`
- weighted moving average weights: `1..N` across the retained points
- slope input: arithmetic mean of consecutive per-minute deltas across the retained points

#### Scenario: Forecast is included when enough history exists
- **WHEN** the system has enough recent monitoring rows to evaluate a forecast horizon
- **THEN** the decision output SHALL include forecast points and a forecasted risk rate for each priority item

#### Scenario: Forecast risk does not become a formal alert automatically
- **WHEN** the forecast indicates likely worsening but the current window has not crossed the formal warning or critical threshold
- **THEN** the decision output SHALL expose a predictive watch state without creating a formal alert notification event

#### Scenario: Forecast degrades gracefully with limited history
- **WHEN** the system lacks enough recent rows to produce a stable forecast
- **THEN** the decision output SHALL omit or down-rank forecast data and report reduced confidence

#### Scenario: Forecast output remains bounded
- **WHEN** forecast computation produces a rate estimate
- **THEN** the forecasted rate SHALL be capped to the valid `0.0..1.0` range before it is returned

### Requirement: Decision guidance SHALL support selectable local and external providers
The system SHALL support a local decision provider by default and MAY use an external provider for narrative enhancement when configured, without making external connectivity the source of truth for prioritization.

The external-provider contract SHALL be constrained to:
- supported providers: `openai`, `anthropic`, `google`
- externally rewritable fields only: `summary`, `top_recommendation`, `problem_explanation`, `forecast_explanation`
- locally authoritative fields: status, ranking, severity, risk score, confidence, current rate, baseline rate, forecast rate, business-impact numeric fields, and evidence selection
- surfaced provider state fields only: mode, provider, model, fallback flag, sanitized error text

#### Scenario: Local provider is the default
- **WHEN** no external provider configuration is present
- **THEN** the system SHALL produce decision guidance entirely from local logic and runtime data

#### Scenario: External provider failure falls back safely
- **WHEN** an external decision provider is configured but returns an error, timeout, or invalid response
- **THEN** the system SHALL fall back to local guidance and surface the provider fallback state in the decision response

#### Scenario: Local scoring remains authoritative
- **WHEN** an external provider is enabled
- **THEN** the system SHALL preserve locally computed priority, severity, formal alert boundaries, and business-impact numeric fields rather than allowing the external provider to override them

#### Scenario: Provider failures do not leak secrets
- **WHEN** an external provider request fails
- **THEN** the decision response SHALL expose only sanitized fallback state and SHALL NOT include API keys, raw provider responses, or full request payloads

### Requirement: Decision guidance SHALL surface deterministic business-impact context
The system SHALL derive structured business-impact context from the top monitoring risk so an operator and reviewer can see what is above normal, who likely owns it, and how many transactions are approximately affected.

#### Scenario: Business-impact fields are present for the top decision
- **WHEN** the decision endpoint returns a current monitoring snapshot
- **THEN** the response SHALL include a top-level `business_impact` object containing `top_metric`, `domain_label`, `likely_owner`, `above_normal_rate`, `warning_gap_rate`, `excess_transactions_now`, and `projected_excess_transactions_horizon`

#### Scenario: Metric-to-business mapping is deterministic
- **WHEN** the top metric is `denied`, `failed`, or `reversed`
- **THEN** the decision output SHALL map that metric to a fixed domain label and likely owner rather than leaving business ownership ambiguous

#### Scenario: Above-normal values do not overstate negative deltas
- **WHEN** the current or forecast rate is at or below baseline
- **THEN** the structured above-normal delta fields SHALL clamp to `0` rather than presenting a negative above-normal value

#### Scenario: Warning gap uses the formal alert threshold definition
- **WHEN** the system computes `warning_gap_rate` for a priority item
- **THEN** it SHALL compute `warning_threshold` using the same baseline-aware warning rule as formal monitoring alerts for that metric and SHALL return `warning_gap_rate = max(0, warning_threshold - current_rate)`

#### Scenario: Forecasted excess transactions use the current window as the volume proxy
- **WHEN** the system computes `projected_excess_transactions_horizon`
- **THEN** it SHALL multiply `forecast_above_normal_rate` by the current decision-window `total` as a deterministic projection proxy rather than introducing separate volume forecasting

### Requirement: Decision guidance SHALL provide separate problem and forecast explanations
The system SHALL explain what is wrong now and what is likely to happen next through distinct narrative fields so the reviewer can distinguish current business impact from forecast interpretation.

#### Scenario: Problem explanation describes the current business consequence
- **WHEN** the decision output identifies a top metric
- **THEN** `problem_explanation` SHALL describe the current above-normal delta, approximate excess transactions, likely owner, and whether the current window is below or above formal alert territory

#### Scenario: Forecast explanation describes projected movement or forecast limitations
- **WHEN** a forecast is available for the top metric
- **THEN** `forecast_explanation` SHALL describe the projected above-normal movement and the expected near-term operational consequence

#### Scenario: Forecast explanation degrades gracefully with limited history
- **WHEN** the system lacks enough recent rows to support a stable forecast
- **THEN** `forecast_explanation` SHALL explain that forecast guidance is limited by insufficient recent history rather than implying normality
