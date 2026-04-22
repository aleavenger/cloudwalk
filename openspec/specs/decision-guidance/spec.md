# decision-guidance Specification

## Purpose
TBD - created by archiving change decision-first-dashboard-alerting. Update Purpose after archive.
## Requirements
### Requirement: Decision guidance SHALL rank current transaction risks
The system SHALL derive operator-facing decision guidance from recent monitoring metrics, alert history, baseline rates, and authorization-code context so the highest-priority issue is visible without manual correlation.

#### Scenario: Highest-risk metric is ranked first
- **WHEN** recent monitoring windows show more than one elevated metric
- **THEN** the decision output SHALL return a priority-ordered list that places the highest-risk metric first and includes severity, risk score, current rate, and baseline rate for each listed item

#### Scenario: Overall status mapping is deterministic
- **WHEN** decision guidance evaluates the latest monitoring state
- **THEN** it SHALL map status to `act_now` when any metric is currently `warning` or `critical`, to `watch` when no metric is `act_now` but at least one metric is current `info` or forecast-elevated, and to `normal` otherwise

#### Scenario: Guidance includes an actionable next step
- **WHEN** the decision output identifies a priority item
- **THEN** the system SHALL include a recommended operator action and a root-cause hint for that item

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
- externally rewritable fields only: `summary`, `top_recommendation`
- locally authoritative fields: status, ranking, severity, risk score, confidence, current rate, baseline rate, forecast rate, evidence selection
- surfaced provider state fields only: mode, provider, model, fallback flag, sanitized error text

#### Scenario: Local provider is the default
- **WHEN** no external provider configuration is present
- **THEN** the system SHALL produce decision guidance entirely from local logic and runtime data

#### Scenario: External provider failure falls back safely
- **WHEN** an external decision provider is configured but returns an error, timeout, or invalid response
- **THEN** the system SHALL fall back to local guidance and surface the provider fallback state in the decision response

#### Scenario: Local scoring remains authoritative
- **WHEN** an external provider is enabled
- **THEN** the system SHALL preserve locally computed priority, severity, and formal alert boundaries rather than allowing the external provider to override them

#### Scenario: Provider failures do not leak secrets
- **WHEN** an external provider request fails
- **THEN** the decision response SHALL expose only sanitized fallback state and SHALL NOT include API keys, raw provider responses, or full request payloads

