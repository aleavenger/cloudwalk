## MODIFIED Requirements

### Requirement: Checkout anomalies SHALL be explained with visual and written conclusions
The submission SHALL include charts and narrative conclusions that compare `today` against historical references for both checkout datasets and identify the most relevant anomalous windows in reviewer-facing language without removing the timestamp evidence required by the challenge brief.

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

#### Scenario: Report wording remains challenge-readable after copy rewrite
- **WHEN** the checkout-analysis section is rewritten for clearer reviewer-facing language
- **THEN** it SHALL still explain the anomaly behavior in plain language
- **AND** it SHALL preserve the explicit checkout hour markers and baseline-comparison evidence needed to satisfy `database/monitoring-test.md`
