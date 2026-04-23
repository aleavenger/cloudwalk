## MODIFIED Requirements

### Requirement: Monitoring service SHALL expose operational monitoring data
The system SHALL expose health, metrics, decision-guidance, and alert-history endpoints that can be consumed by reviewers and dashboard tooling.

#### Scenario: Decision endpoint exposes operator guidance and business impact
- **WHEN** a client requests decision guidance
- **THEN** the response SHALL return a current decision snapshot that includes `overall_status`, `top_recommendation`, `summary`, `problem_explanation`, `forecast_explanation`, `business_impact`, `priority_items`, `forecast_points`, `recent_evidence`, and provider state
- **AND** `business_impact` SHALL include `top_metric`, `domain_label`, `likely_owner`, `above_normal_rate`, `warning_gap_rate`, `excess_transactions_now`, and `projected_excess_transactions_horizon`
- **AND** each priority item SHALL include `above_normal_rate`, `forecast_above_normal_rate`, `excess_transactions_now`, `projected_excess_transactions_horizon`, and `warning_gap_rate`

#### Scenario: Decision endpoint keeps raw numeric fields machine-readable
- **WHEN** a client consumes decision guidance programmatically
- **THEN** the response SHALL continue exposing raw numeric rate, confidence, and business-impact fields rather than replacing them with human-formatted strings
