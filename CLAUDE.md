# Claude Instructions - CloudWalk

Read in order before non-trivial changes:
1. `RULES.md`
2. `AI_GUARDRAILS.md`
3. `INVARIANTS.md`
4. `SYSTEM_MAP.md`

## Required behavior

- Keep changes minimal and additive by default.
- Preserve API auth, validation, and response contracts.
- Preserve one-click reviewer workflow.
- Update docs when behavior changes.

## High-risk change protocol

For auth, alert-threshold semantics, bootstrap flow, or network exposure changes:
1. Explain risk surface
2. Provide rollback plan
3. Wait for explicit approval
