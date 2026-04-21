# AI Guardrails - CloudWalk Repository Safety

This file governs AI assistant behavior in this repository.

## 1. Core Safety Rules

- `RULES.md` is the canonical AI rules baseline.
- Keep changes minimal and scoped to the user request.
- Do not weaken endpoint authentication or payload validation.
- Do not add secret-bearing logs, debug dumps, or unsafe output paths.
- Do not silently alter evaluator-facing contracts in tests, scripts, or README.

## 2. API and Alert Safety

- `/monitor` must remain input-validated and bounded.
- Do not bypass cooldown or baseline logic to force alerts.
- Do not modify response schemas without explicit request and doc updates.

## 3. Deployment and Runtime Safety

- Keep compose defaults localhost-only unless explicitly requested otherwise.
- Preserve bootstrap fail-fast behavior in `docker/api-entrypoint.sh`.
- Preserve deterministic artifact generation for reviewer startup flow.

## 4. Prohibited Changes Without Explicit Request

- Removing API key protection from protected endpoints.
- Disabling request-size limits or validation guards.
- Replacing generated artifact flow with manual-only steps.
- Introducing external services or dependencies not required by the challenge.

## 5. Required Docs Sync

If behavior changes, update in the same change set:
- `SYSTEM_MAP.md`
- `INVARIANTS.md`
- `README.md`

If docs and code disagree, report and fix drift.
