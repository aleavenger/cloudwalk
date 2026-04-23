## 1. Decision contract and business-impact logic

- [x] 1.1 Extend `DecisionResponse` and related decision models with `problem_explanation`, `forecast_explanation`, `business_impact`, and the new per-priority business-impact fields.
- [x] 1.2 Implement deterministic business-impact derivation in the decision engine for above-normal delta, projected excess transactions, warning-gap distance, and top-metric owner/domain mapping.
- [x] 1.3 Update local narrative generation so the top issue explains current business meaning, why it is or is not alerting, and the forecast outlook or forecast limitation.
- [x] 1.4 Expand the external-provider prompt/response path so only the four narrative strings may be rewritten.

## 2. API, guardrails, and tests

- [x] 2.1 Update `/decision` endpoint tests and contract assertions for the new fields and local-authoritative boundaries.
- [x] 2.2 Add coverage for elevated-but-not-alerting windows so the output explicitly explains above-normal behavior without formal alert escalation.
- [x] 2.3 Add coverage for limited-history forecast cases, projected excess-transaction calculations, and zero-clamped above-normal values.
- [x] 2.4 Update guardrail-oriented tests and docs for the broader externally rewritable narrative surface.

## 3. Dashboard and reviewer bootstrap

- [x] 3.1 Add a reviewer-facing business-impact panel to the Grafana dashboard and expose the new narrative fields in the decision snapshot area.
- [x] 3.2 Update the priority queue to show above-normal delta, excess affected transactions, projected excess transactions, warning gap, and human-readable percent formatting.
- [x] 3.3 Update Grafana dashboard contract checks so the new fields remain provisioned and machine-backed.
- [x] 3.4 Change the reviewer bootstrap flow to prefer external AI by default and print honest local-fallback messaging.

## 4. Documentation sync and verification

- [x] 4.1 Update `README.md`, `SYSTEM_MAP.md`, `INVARIANTS.md`, and `docs/monitoring-methodology.md` to document business-impact fields, narrative behavior, and reviewer bootstrap expectations.
- [x] 4.2 Run the targeted API tests and dashboard contract checks covering the broadened decision response and reviewer flow.
- [x] 4.3 Run the reviewer-visible validation path, including Grafana dashboard verification when Playwright tooling is available.
