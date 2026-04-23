# CloudWalk Monitoring Analyst Challenge

## Anomaly detection and transaction alerting

Reviewer presentation for the CloudWalk monitoring analyst challenge.

Evidence in this deck comes from:

- `database/` source CSVs
- `database/report/` generated anomaly tables
- `charts/` generated checkout visualizations
- `grafana/` dashboard configuration
- FastAPI monitoring and decision endpoints

---

# The Problem

CloudWalk needs a monitoring workflow that can:

- identify unusual checkout behavior against historical hourly references
- detect abnormal denied, failed, and reversed transaction rates
- return an alert recommendation through an API
- report formal alerts automatically to an operations-facing channel
- explain the evidence clearly enough for a reviewer or operator to act

The challenge is not only detection. It is also deciding which anomalies matter enough to interrupt a team.

---

# What Was Built

The repository implements an end-to-end local monitoring flow:

- SQL-style checkout anomaly analysis with generated CSV artifacts
- generated SVG charts for checkout behavior
- FastAPI service for aggregate and single-transaction monitoring
- baseline-aware alert engine with cooldown suppression
- Grafana dashboard for decision, forecast, alert, and metric views
- local mock team receiver for webhook delivery checks

Primary reviewer entrypoint:

```bash
./scripts/reviewer_start.sh
```

---

# Evidence Map

Canonical data:

- `database/checkout_1.csv`
- `database/checkout_2.csv`
- `database/transactions.csv`
- `database/transactions_auth_codes.csv`

Generated evidence:

- `database/report/checkout_1_anomaly.csv`
- `database/report/checkout_2_anomaly.csv`
- `charts/checkout_1.svg`
- `charts/checkout_2.svg`
- `grafana/dashboard.json`
- `report/technical_report.md`

Runtime logs are not used as canonical evidence because smoke tests and manual replays can append synthetic alert records.

---

# Checkout Findings

`checkout_2` is the stronger structural anomaly:

- `08h`: 25 today vs 8.51 baseline, +193.77%
- `09h`: 36 today vs 18.26 baseline, +97.15%
- `15h`, `16h`, and `17h`: 0 today against material baselines

`checkout_1` shows higher net uplift but less structural disruption:

- total today: 526 vs 431.58 baseline, +21.88%
- largest uplift at `17h`: 45 today vs 23.90 baseline
- other material uplift at `10h`, `12h`, and `15h`

Chart evidence:

![Checkout 1 anomaly chart](../charts/checkout_1.svg)

---

# Checkout 2 Pattern

`checkout_2` shows a morning surge followed by a sharp afternoon gap.

This pattern is operationally more suspicious than a single high hour because it combines:

- a demand surge at `08h` and `09h`
- continued elevated behavior through midday
- complete dropouts at `15h`, `16h`, and `17h`

That suggests the reviewer should inspect time-specific business or system behavior, not just total daily volume.

![Checkout 2 anomaly chart](../charts/checkout_2.svg)

---

# Transaction Baseline

The transaction dataset is continuous and internally consistent:

- data range: `2025-07-12 13:45:00` to `2025-07-15 13:44:00`
- minute buckets: 4,320
- total transactions: 544,320
- approved transactions: 504,622
- overall approval rate: 92.7%

Overall status mix:

- denied: 29,957, about 5.5%
- reversed: 4,241, about 0.8%
- failed: 270, about 0.05%

The case is therefore not a full-system outage. It is concentrated abnormal behavior inside otherwise healthy traffic.

---

# Incident Shape

Before cooldown, the dataset contains:

- 315 warning or critical minutes
- 213 denied-related alertable minutes
- 68 reversed-related alertable minutes
- 37 failed-related alertable minutes

If the full dataset is replayed through cooldown rules:

- 166 formal alerts would be emitted
- 136 warning alerts
- 30 critical alerts

Denied behavior dominates the incident surface. Failed and reversed spikes are real but smaller and more localized.

---

# Denied Incidents

The strongest denied episodes point to issuer/customer payment friction.

Key episodes:

- `2025-07-13 21:20-21:58`: 753 denied out of 2,941, about 25.6%, dominated by auth code `59 Suspected fraud`
- `2025-07-13 08:38-09:17`: 682 denied out of 2,503, about 27.2%, dominated by auth code `51 Insufficient funds`
- `2025-07-12 17:09-17:24`: 534 denied out of 1,773, about 30.1%, dominated by auth code `51`

Anchor minute:

- `2025-07-12 17:18`: 54 denied out of 149, denied rate 36.24%

---

# Failed And Reversed Incidents

Failed spike:

- `2025-07-15 04:30`: 10 failed out of 115
- failed rate: 8.70%
- likely owner: platform/gateway engineering
- interpretation: processor, application, or network instability

Reversed spikes:

- `2025-07-14 01:53`: 7 reversed out of 131
- `2025-07-14 06:33`: 7 reversed out of 141
- likely owner: finance/reconciliation ops
- interpretation: reconciliation, settlement, or duplicate-processing issue

These incidents are material, but the denied episodes are the largest business-impact pattern.

---

# Alert Model

The alert model is deterministic and baseline-aware:

- baseline: previous 60 complete minutes
- minimum total volume: 80 transactions
- minimum metric count: 3 denied, failed, or reversed events
- warning threshold: max configured floor, baseline x 2.0
- critical threshold: max configured critical floor, baseline x 3.0
- cooldown: suppress repeated metric + severity alerts for 10 minutes

This keeps the system sensitive to real spikes while reducing noise from low-volume minutes.

---

# Dashboard Decision State

The current focused dashboard state is normal.

Latest focused minute:

- timestamp: `2025-07-15 13:44:00`
- denied rate: 6.43%
- denied baseline: 5.01%
- estimated excess denied transactions now: about 2
- forecasted denied rate within 30 minutes: 7.02%

Interpretation:

- there is mild denied elevation
- it remains below formal warning threshold
- no immediate action is required at the latest dashboard focus point

---

# Operational Controls

The implementation protects the reviewer runtime with:

- localhost-only Docker port bindings
- optional API key on monitoring, metrics, alerts, and decision endpoints
- request body size limits
- count and auth-code validation
- aggregate-only alert metadata
- webhook delivery status reported separately from alert detection

Runtime log files under `logs/` are operational artifacts. They are useful for local checks, but not the source of truth for the case findings.

---

# Conclusion

The case shows concentrated payment-friction incidents, plus smaller platform and reconciliation spikes.

What the system proves:

- checkout anomalies are reproducible from SQL-style baseline comparisons
- transaction alerting catches denied, failed, and reversed behavior above normal
- cooldown reduces repeated alert noise
- auth-code enrichment explains likely ownership and triage path
- Grafana and `/decision` translate raw rates into reviewer-facing action guidance

Bottom line: the monitoring workflow identifies business-relevant smoke without treating every noisy minute as fire.
