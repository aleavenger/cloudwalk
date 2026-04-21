# Gemini Instructions - CloudWalk

This repository has strict behavior contracts.

Before changes, read:
1. `RULES.md`
2. `AI_GUARDRAILS.md`
3. `INVARIANTS.md`
4. `SYSTEM_MAP.md`

## Non-negotiable rules

- Do not weaken API auth or validation.
- Do not break one-click startup and artifact generation.
- Do not leak keys or raw sensitive payload content to logs.
- Keep documentation synchronized with behavior.
