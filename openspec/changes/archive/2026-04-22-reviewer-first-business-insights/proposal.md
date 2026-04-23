## Why

The current decision layer is operationally correct, but it still makes a reviewer do too much interpretation. The dashboard can rank risk and show forecast data, yet it does not explicitly answer the reviewer-facing questions that matter most during evaluation: what is above normal, why it matters to the business, why it is or is not a formal alert yet, who likely owns the next step, and what the next 30 minutes could mean in practical terms.

This change makes the monitoring experience feel more decision-ready and reviewer-ready. It adds deterministic business-impact signals, richer problem and forecast explanation, clearer human-readable formatting in Grafana, and bootstrap messaging that prefers the richer external-AI reviewer path without weakening the local-safe fallback.

## What Changes

- Add a business-impact layer to decision guidance with explicit above-normal delta, excess affected transactions, threshold gap, domain label, and likely owner.
- Extend `GET /decision` with `problem_explanation`, `forecast_explanation`, and a top-level `business_impact` object while keeping raw numeric fields machine-readable.
- Expand the optional external-provider rewrite scope from `summary` and `top_recommendation` to the four narrative fields only.
- Redesign the Grafana decision panels around reviewer-facing business meaning, including a business-impact panel and human-readable percentage formatting.
- Update the reviewer bootstrap flow to prefer external AI by default and explain local mode as a safe deterministic fallback with less narrative polish.
- Synchronize docs, invariants, and tests with the broadened decision contract and reviewer-facing behavior.

## Capabilities

### Modified Capabilities
- `decision-guidance`: add business-impact context and richer narrative output while preserving local-authoritative scoring.
- `transaction-alert-monitoring`: extend the `GET /decision` contract with additional structured decision data.
- `monitoring-visualization-and-reporting`: make the dashboard explicitly show above-normal business impact and reviewer-facing explanations.
- `reviewer-one-click-runtime`: prefer external AI in the reviewer bootstrap flow and clarify local fallback messaging.

## Impact

- Backend decision models and logic in `app/`.
- Grafana dashboard assets and contract tests.
- Reviewer bootstrap script and first-login messaging.
- Repository documentation and invariants that describe the decision contract and reviewer flow.
