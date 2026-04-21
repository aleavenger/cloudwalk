## Why

The CloudWalk monitoring test expects more than isolated charts or a toy API: it asks for a coherent monitoring workflow that detects anomalies, explains them with data, and reports them in a way an operations team could use. This change is needed now because the repository currently contains only the challenge brief and raw CSVs, with none of the implementation or documentation artifacts required to submit a strong, runnable solution.

## What Changes

- Add a checkout anomaly analysis package that uses SQL and visualizations to explain abnormal hourly sales behavior in `checkout_1.csv` and `checkout_2.csv`.
- Add a transaction monitoring service that evaluates per-minute status behavior, recommends alerts for denied, failed, and reversed spikes, and exposes monitoring endpoints.
- Add a monitoring visualization and reporting layer that provides a Grafana dashboard, alert history, and a technical report suitable for the repository deliverable.
- Add project documentation, runnable setup instructions, and validation coverage so the submission is easy to review and demonstrate.
- Add lightweight security hardening for local-safe operation: optional API-key protection, payload bounds, safe logging, and pinned dependency/plugin versions.

## Capabilities

### New Capabilities
- `checkout-anomaly-analysis`: Analyze hourly checkout datasets with SQL-derived baselines, anomaly scoring, and explanatory charts.
- `transaction-alert-monitoring`: Detect and classify anomalous transaction windows, expose monitoring endpoints, and generate alert recommendations.
- `monitoring-visualization-and-reporting`: Present metrics, alerts, and findings through Grafana-ready data feeds plus submission documentation.

### Modified Capabilities
None.

## Impact

- Adds a Python service, SQL queries, dashboard assets, report content, and tests to the repository.
- Introduces public monitoring interfaces for health, metrics, alerts, and anomaly recommendation endpoints.
- Uses the provided CSV files as the canonical dataset for analysis, alert logic, and dashboard content.
- Requires local Python dependencies and a Grafana import workflow for end-to-end demonstration.
- Adds explicit guardrails for endpoint access, request-size limits, and logging hygiene.
