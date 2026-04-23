# CloudWalk Unified AI Rules

This file is the canonical ruleset for AI assistants working in this repository.

Companion contracts:
- SYSTEM_MAP.md (architecture)
- INVARIANTS.md (safety and behavioral invariants)
- AI_GUARDRAILS.md (production and data-handling policy)

## 1. Required Pre-Change Read Order

Before proposing or implementing non-trivial changes, read in this order:
1. RULES.md
2. AI_GUARDRAILS.md
3. INVARIANTS.md
4. SYSTEM_MAP.md

If instructions conflict, precedence is:
1. INVARIANTS.md
2. AI_GUARDRAILS.md
3. RULES.md
4. AI-specific instruction files

## 2. Safety Baseline

- Treat this repository as reviewer-facing monitoring software, not a throwaway demo.
- Prefer additive and minimal changes unless a rewrite is explicitly requested.
- Do not weaken API authentication, payload validation, or file-write boundaries.
- Do not log secrets or raw sensitive payload fragments.
- Keep localhost-only exposure defaults in Docker Compose.

## 3. API Contract Baseline

- `/health` is public.
- `/monitor`, `/metrics`, and `/alerts` require `X-API-Key` when `MONITORING_API_KEY` is configured.
- Do not silently change response schemas in `app/models.py`.
- Keep FastAPI route paths stable unless documentation is updated in the same change.

## 4. Alerting Behavior Baseline

- Alert decisions must remain baseline-driven and deterministic for the same input.
- Cooldown deduplication is part of the contract; avoid duplicate alerts for the same metric+severity window.
- `logs/alerts.log` must contain only aggregated metadata (no API keys, no raw request bodies).

## 5. Data and Artifact Baseline

- `database/transactions.csv` and `database/transactions_auth_codes.csv` are canonical inputs for runtime baselines.
- `scripts/checkout_analysis.py` and `scripts/generate_checkout_charts.py` must stay runnable in bootstrap flow.
- Docker API entrypoint must continue generating report/chart artifacts before starting Uvicorn.

## 6. Documentation Drift Policy

If behavior changes, update affected docs in the same change set:
- SYSTEM_MAP.md
- INVARIANTS.md
- AI_GUARDRAILS.md
- README.md
- docs/monitoring-methodology.md

If code and docs diverge, report and fix drift in the same PR/change.

Additional required maintenance rules:
- If logic, thresholds, dataset paths, generated artifact paths, or anomaly conclusions change, review and update `docs/monitoring-methodology.md`.
- If methodology link placement or user-facing explanation changes, review and update `README.md` in the same change.

## 7. High-Risk Change Protocol

Before changes to API auth, alert logic thresholds, Docker startup flow, or monitoring data contracts:
1. Explain risk surface
2. Provide rollback plan
3. Wait for explicit approval

## 8. Test Execution Baseline

- Do not assume global tooling availability.
- Prefer repository virtualenv execution when available:
  - `.venv/bin/python -m pytest`

## 9. Delegation and Model Selection

- For coding work, use subagents whenever the task contains any bounded separable subtask that can run in parallel without lowering quality.
- Do not skip subagents for convenience on multi-part coding work; keep work local only when the task is truly tiny or fully serial.
- Prefer cheaper models when they can complete the task without reducing result quality.
- Prefer `codex` models for code implementation, code editing, and code debugging.
- Prefer `gpt` models for planning, review, synthesis, and other reasoning-heavy work.
- For read-only scavenging tasks such as web lookup, repo scraping, log inspection, or database inspection, use the cheapest capable model and avoid high-end models when no deeper reasoning is required.
- Default coding ladder:
  - `gpt-5.1-codex-mini` for bounded low-risk code tasks
  - `gpt-5.2-codex` for standard coding work
  - `gpt-5.3-codex` or stronger only for materially complex or high-risk code tasks
- Default reasoning ladder:
  - `gpt-5.2` for standard planning, review, and analysis
  - `gpt-5.4` only when the reasoning difficulty clearly justifies escalation
- If a preferred model is unavailable, use the next available model that preserves the same lane and cost discipline before crossing to a more expensive or different-family model.
- Higher-priority host/tool constraints still apply; repository policy does not override platform-enforced limits on delegation or model availability.

## 10. AI-Specific Adapters

AI-specific files may add workflow details but must not contradict this file:
- AGENTS.md
- CLAUDE.md
- GEMINI.md
- .github/copilot-instructions.md
