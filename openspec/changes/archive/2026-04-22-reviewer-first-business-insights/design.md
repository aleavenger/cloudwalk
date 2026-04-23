## Context

CloudWalk already has a deterministic decision engine, a decision-first dashboard, and an optional external-AI path. That foundation is technically strong, but the reviewer experience still leans too hard on inference. A reviewer can see rates, baselines, risk score, and forecast points, then manually infer business consequence and operator next step. The user wants the system to present that interpretation directly, while still keeping the local monitoring math and alert boundaries trustworthy.

This change must respect the existing repository constraints:
- formal alert rules remain based on the current anomaly engine and must stay separate from predictive guidance
- local scoring remains complete and authoritative even when external AI is enabled
- reviewer startup remains local-safe, Docker-based, and secret-hygienic
- API and dashboard contracts must stay explicit enough for tests and docs to enforce them

There is one deliberate contract expansion in this change: the external provider may rewrite more narrative fields than today. That must be explicit in specs, docs, invariants, and tests so implementation does not drift into ambiguous AI behavior.

## Goals / Non-Goals

**Goals:**
- Make `/decision` explain current risk in business terms rather than only operational terms.
- Make “above normal” explicit and consistent across the API contract, Grafana rendering, and reviewer narrative.
- Show why a metric is not a formal alert yet when it is elevated but still below threshold.
- Surface approximate excess affected transactions and likely business owner for the top issue.
- Prefer the richer external reviewer path during bootstrap while keeping local mode safe and fully functional.

**Non-Goals:**
- Replacing the anomaly engine, baseline computation, or cooldown semantics.
- Turning forecast/watch guidance into formal alert history.
- Replacing raw numeric API fields with human-formatted strings.
- Introducing revenue-based business impact calculations; the dataset does not include transaction value.
- Making external AI mandatory for the reviewer flow.

## Decisions

### Add a deterministic business-impact layer on top of the decision engine
The decision engine already computes current rate, baseline rate, forecast rate, confidence, and ranking. This change adds business-facing derivatives instead of asking the dashboard or external AI to infer them ad hoc.

Locked additions:
- per-priority fields:
  - `above_normal_rate = max(0, current_rate - baseline_rate)`
  - `forecast_above_normal_rate = max(0, forecast_rate - baseline_rate)` when forecast exists, else `null`
  - `excess_transactions_now = round(above_normal_rate * total)`
  - `projected_excess_transactions_horizon = round(forecast_above_normal_rate * total)` when forecast exists, else `null`
  - `warning_gap_rate = max(0, warning_threshold - current_rate)`
- top-level `business_impact` object:
  - `top_metric`
  - `domain_label`
  - `likely_owner`
  - `above_normal_rate`
  - `warning_gap_rate`
  - `excess_transactions_now`
  - `projected_excess_transactions_horizon`

Locked metric-to-business mappings:
- `denied` → domain `customer payment friction`, owner `issuer/acquirer ops`
- `failed` → domain `processing reliability`, owner `platform/gateway engineering`
- `reversed` → domain `reconciliation integrity`, owner `finance/reconciliation ops`

These mappings stay local-authoritative and deterministic.

### Expand the narrative contract, not the scoring contract
The existing output exposes `summary` and `top_recommendation`. That is not enough to separately explain what is wrong now and what the forecast implies next.

Locked additions:
- `problem_explanation`
- `forecast_explanation`

Narrative responsibilities:
- `summary`: compact overall monitoring story
- `top_recommendation`: short operator next step
- `problem_explanation`: why the top metric matters now, including above-normal delta, business meaning, likely owner, and whether it is below or above formal alert territory
- `forecast_explanation`: expected near-term movement, projected excess transactions when available, or a clear explanation that forecast guidance is limited by insufficient history

Raw numeric fields remain separate and authoritative.

### Broaden external rewrite scope only for narrative strings
The current invariant only allows external rewriting of `summary` and `top_recommendation`. This change deliberately broadens that contract, but only within the narrative boundary.

Locked external rewrite scope:
- `summary`
- `top_recommendation`
- `problem_explanation`
- `forecast_explanation`

Locked local-authoritative fields:
- overall status
- ranking
- severity
- risk score
- confidence
- current, baseline, and forecast rates
- business-impact numeric fields
- evidence selection
- provider fallback state
- formal alert boundaries

This keeps external AI useful for reviewer polish without letting it become the source of truth.

### Define “above normal” as percentage-point delta above baseline
The user asked what “above normal number” should mean. This change locks a single meaning across backend and dashboard.

Locked definition:
- `above normal = positive rate delta above baseline`
- presentation is in percentage points, for example `+1.4 pp above normal`
- negative deltas clamp to `0` in structured business-impact fields

Alternative rejected:
- baseline multiple (`1.3x normal`) as the primary expression, because it is less intuitive for a reviewer scanning a dashboard quickly.

### Keep the API machine-readable and do human formatting in Grafana
The user wants confidence shown as a percentage and rates to be easier to read. The existing numeric fields should remain intact for tests and downstream machine consumers.

Locked formatting approach:
- API continues returning raw numeric rates and confidence
- Grafana renders:
  - `confidence` as percent
  - rates as percent
  - above-normal and threshold-gap fields as percentage points
  - impact counts as whole numbers
- no existing numeric fields are replaced by strings

### Redesign the top dashboard story around reviewer questions
The dashboard already has a decision-first layout, so this change refines the content rather than replacing the structure wholesale.

Locked dashboard outcomes:
- add a `Business Impact` panel sourced from `GET /decision`
- surface `problem_explanation` and `forecast_explanation` in the decision snapshot area
- update the priority queue to show above-normal delta, excess transactions, projected excess transactions, and warning gap
- make it visually obvious why a metric can be elevated without yet being a formal alert

Reviewer-facing questions the dashboard must answer directly:
1. What is above normal right now?
2. What business function is affected?
3. Why is this not a formal alert yet, or why is it alerting now?
4. What will likely happen next if the current trend continues?

### Prefer external AI in bootstrap, but describe local mode honestly
The bootstrap script is the evaluator’s first touchpoint. It should guide them toward the richer experience without implying local mode is broken.

Locked bootstrap behavior changes:
- prompt default changes from `local` to `external`
- if external AI is not configured, bootstrap falls back to `local`
- fallback messaging must say local mode is deterministic and fully functional for monitoring, but less polished for reviewer-facing narrative
- first-login notes must explain the distinction between richer external narrative and local-safe fallback

The repository’s baseline runtime configuration remains local-safe; only the guided reviewer bootstrap changes its preferred default.

## Risks / Trade-offs

- [Business insight could overclaim certainty] → Mitigation: keep business-impact fields derived only from dataset-backed rates and counts, and use confidence-aware forecast wording.
- [Broader external rewrite scope could weaken guardrails] → Mitigation: constrain rewriting to four narrative strings only and update invariants/tests together.
- [Dashboard could become noisier] → Mitigation: keep the business-impact panel focused on the top metric and present deeper detail in the priority queue rather than duplicating everything everywhere.
- [Bootstrap preference for external mode could confuse offline reviewers] → Mitigation: make fallback automatic and message local mode as safe and complete for monitoring behavior.

## Migration Plan

1. Extend decision response models and decision-engine output with business-impact fields and the two new narrative fields.
2. Update local narrative generation to explain above-normal delta, operator ownership, business meaning, threshold proximity, and forecast limitation when needed.
3. Expand external-provider prompt/response handling to allow rewriting the four narrative strings only.
4. Update `GET /decision` tests and contract assertions for the broadened response shape and local-authoritative boundaries.
5. Update Grafana panels and field formatting for business impact, percent rendering, and explicit above-normal visibility.
6. Update reviewer bootstrap messaging and defaults for preferred external mode with safe local fallback.
7. Update `SYSTEM_MAP.md`, `INVARIANTS.md`, `README.md`, and `docs/monitoring-methodology.md` to reflect the new decision contract and reviewer story.

## Open Questions

None. The change proceeds with deterministic business-impact logic, Grafana-side formatting, and external AI limited to narrative rewriting.
