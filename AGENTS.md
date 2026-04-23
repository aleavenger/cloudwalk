# CloudWalk AI Agents

This repository uses AI agents for implementation, review, and debugging.

Architecture contracts:
- `SYSTEM_MAP.md` -> architecture map
- `INVARIANTS.md` -> enforced behavior/safety rules
- `AI_GUARDRAILS.md` -> operational AI constraints

Agents must read these files before non-trivial changes.

## Delegation and Model Policy

- For coding work, always use subagents when there is any bounded separable implementation, debugging, or verification task that can run in parallel without reducing quality.
- Keep work local only for truly tiny fixes or work that is fully serial and would not benefit from delegation.
- Prefer cheaper models when they can complete the task without making results worse.
- Prefer `codex` models for coding tasks and `gpt` models for reasoning, planning, review, and synthesis.
- Do not use high-end models for scraping the web, scavenging the repository, or scavenging databases/logs when a cheaper capable model can do the job.
- Model ladder:
  - coding: `gpt-5.1-codex-mini` first, then `gpt-5.2-codex`, then stronger `codex` only for materially complex or high-risk work
  - reasoning: `gpt-5.2` first, escalate to `gpt-5.4` only when needed
- If a preferred model is unavailable, use the next available model that follows the same lane and cost rules.

## Debugging Protocol

1. Identify observable failure (test, response, log, or generated artifact).
2. Locate exact code path.
3. Trace execution end-to-end.
4. Isolate root cause.
5. Apply minimal safe fix.

## Mandatory Checks

- Auth: `build_api_key_guard()` behavior and endpoint dependencies.
- Payload bounds: middleware and model/endpoint validations.
- Alert behavior: baseline, thresholds, cooldown suppression.
- Log hygiene: no key leakage, aggregated-only metadata.
- Bootstrap flow: report+chart generation before API startup.
- UI/runtime validation: for dashboard or frontend-visible changes, run a Playwright check before closing the task (when Playwright tooling is available in the environment).

## Documentation Rule

When changing runtime behavior, update `SYSTEM_MAP.md` and `INVARIANTS.md` in the same change.
