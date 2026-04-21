## ADDED Requirements

### Requirement: Checkout anomaly baselines SHALL be reproducible from SQL
The submission SHALL provide a SQL-based analysis for `checkout_1.csv` and `checkout_2.csv` that preserves the original hourly comparison fields and computes a historical baseline, absolute deviation, and relative deviation for each hour.

#### Scenario: SQL output includes anomaly comparison fields
- **WHEN** the checkout analysis query is run against either checkout dataset
- **THEN** the result SHALL include each hour, the original reference columns, a computed baseline, an absolute deviation value, and a relative deviation value

#### Scenario: Low-volume hours remain visible in the analysis
- **WHEN** an hour has a small historical baseline or low current count
- **THEN** the SQL output SHALL still include that hour so the reporting layer can distinguish meaningful spikes from low-volume noise

### Requirement: Checkout anomalies SHALL be explained with visual and written conclusions
The submission SHALL include charts and narrative conclusions that compare `today` against historical references for both checkout datasets and identify the most relevant anomalous windows.

#### Scenario: Each checkout dataset has its own chart
- **WHEN** the repository deliverables are reviewed
- **THEN** the submission SHALL contain at least one visualization for `checkout_1.csv` and at least one visualization for `checkout_2.csv`

#### Scenario: The report identifies the stronger anomaly case
- **WHEN** the written conclusions are read
- **THEN** the report SHALL explicitly compare the two checkout datasets and state which one shows the stronger anomalous behavior with timestamp-based evidence

#### Scenario: Checkout_2 morning spike is explicitly reported
- **WHEN** the report summarizes strongest checkout anomalies
- **THEN** it SHALL include the `08h` and `09h` surge in `checkout_2.csv` as a primary anomaly example

#### Scenario: Checkout_1 elevated period is explicitly reported
- **WHEN** the report summarizes checkout_1 behavior
- **THEN** it SHALL include at least one elevated window from `10h`, `12h`, `15h`, or `17h` with baseline comparison context
