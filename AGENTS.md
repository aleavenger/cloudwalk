# CloudWalk AI Agents

This repository uses AI agents for implementation, review, and debugging.

Architecture contracts:
- `SYSTEM_MAP.md` -> architecture map
- `INVARIANTS.md` -> enforced behavior/safety rules
- `AI_GUARDRAILS.md` -> operational AI constraints

Agents must read these files before non-trivial changes.

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

## Documentation Rule

When changing runtime behavior, update `SYSTEM_MAP.md` and `INVARIANTS.md` in the same change.
