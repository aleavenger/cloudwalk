## 1. Project Setup

- [x] 1.1 Create the repository layout for application code, SQL artifacts, Grafana assets, report content, charts, and tests.
- [x] 1.2 Add the Python project configuration and dependencies required for FastAPI, data processing, chart generation, and testing, with pinned versions.
- [x] 1.3 Add a configuration module that resolves dataset paths, alert defaults, and local runtime settings.
- [x] 1.4 Add security configuration defaults for `127.0.0.1` binding, optional `MONITORING_API_KEY`, and payload-limit constants.

## 2. Checkout Analysis

- [x] 2.1 Implement SQL queries for checkout baseline, absolute deviation, and relative deviation calculations for both hourly checkout datasets.
- [x] 2.2 Build a reusable analysis script or module that loads the checkout CSVs and produces the derived anomaly tables used by the report.
- [x] 2.3 Generate one chart for `checkout_1.csv` and one chart for `checkout_2.csv` comparing today against the historical reference series.
- [x] 2.4 Write the checkout findings section that identifies the strongest anomaly windows and compares the two datasets with timestamp-based evidence.

## 3. Transaction Aggregation and Alert Logic

- [x] 3.1 Implement CSV loaders for `transactions.csv` and `transactions_auth_codes.csv` with minute-level aggregation helpers.
- [x] 3.2 Add SQL artifacts for transaction status pivoting, rate calculation, and anomaly-oriented drilldown queries.
- [x] 3.3 Implement the baseline-aware anomaly engine using fixed parameters (60-minute baseline, minimum totals, floor rates, warning/critical multipliers).
- [x] 3.4 Add severity classification rules and cooldown-based deduplication for repeated alerts.
- [x] 3.5 Implement auth-code enrichment so anomalous windows include the leading authorization codes for operator triage.

## 4. Monitoring Service

- [x] 4.1 Create the FastAPI application bootstrap and health endpoint.
- [x] 4.2 Implement Pydantic request/response models for `/monitor`, `/metrics`, and `/alerts` using the locked schema fields and enums.
- [x] 4.3 Implement the monitoring endpoint that accepts a transaction window and returns rates, baseline rates, triggered metrics, severity, and alert recommendation.
- [x] 4.4 Implement the metrics endpoint returning `rows[*]` data for dashboard panels and the alert-history endpoint returning `alerts[*]` records.
- [x] 4.5 Implement API-key middleware or dependency guard for `/monitor`, `/metrics`, and `/alerts`, leaving `/health` public.
- [x] 4.6 Enforce request-size and field-size limits for `POST /monitor` and return validation errors for bound violations.
- [x] 4.7 Add a notifier interface with a default local logging sink that records automatic alert reporting attempts with redacted, aggregated fields only.

## 5. Dashboard and Submission Assets

- [x] 5.1 Create the Grafana dashboard JSON covering transaction volume, denied rate, failed rate, reversed rate, active alert state, and recent alerts.
- [x] 5.2 Configure and document `yesoreyeram-infinity-datasource` with endpoint mappings to `/metrics` (`rows[*]`) and `/alerts` (`alerts[*]`) using a pinned plugin version.
- [x] 5.3 Write the technical report sections for methodology, transaction anomaly findings, auth-code drilldown, and limitations.
- [x] 5.4 Capture dashboard and analysis screenshots that include the known anomaly windows called out in the specs.
- [x] 5.5 Write the README with architecture summary, startup steps, and pointers to the report, SQL, and dashboard assets.

## 6. Validation and Final Polish

- [x] 6.1 Add API tests for healthy windows, anomalous windows, and low-volume suppression behavior.
- [x] 6.2 Add tests for cooldown deduplication and alert-history recording.
- [x] 6.3 Add contract tests for `/monitor` validation (`422` cases) and response payload shape for `/metrics` and `/alerts`.
- [x] 6.4 Add fixture-driven acceptance tests for known dataset spikes: denied at `2025-07-12 17:18:00`, failed at `2025-07-15 04:30:00`, and reversed at `2025-07-14 06:33:00`.
- [x] 6.5 Add checkout acceptance assertions for `checkout_2` `08h`/`09h` and one elevated `checkout_1` window in the report outputs.
- [x] 6.6 Add access-control tests for missing/invalid/valid API key paths and unauthenticated `/health`.
- [x] 6.7 Add payload-limit tests for oversized bodies, oversized auth-code maps, and out-of-range count values.
- [x] 6.8 Add logging-safety tests/assertions to confirm raw payloads and secrets are not persisted.
- [ ] 6.9 Run the local test suite and fix any implementation or contract issues uncovered by the results.
- [x] 6.10 Review the repository for submission completeness so all required deliverables are present and runnable.
