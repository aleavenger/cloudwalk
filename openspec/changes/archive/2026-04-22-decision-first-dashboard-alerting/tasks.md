## 1. Decision engine foundation

- [x] 1.1 Extend `app/config.py`, `.env.example`, and Compose/runtime wiring with decision-engine mode, forecast horizon, and optional external provider settings.
- [x] 1.2 Add decision response models and supporting types in `app/models.py` for overall status, priority items, forecast output, evidence, and provider state.
- [x] 1.3 Implement a local `DecisionEngine` that uses the locked `normal/watch/act_now` mapping, bounded `0..100` risk scoring, and deterministic priority ordering.
- [x] 1.4 Implement the deterministic forecast path with the locked defaults: `15` minute lookback, `30` minute horizon, `5` minute step, `5` minimum history points, weighted moving average, and mean per-minute slope.
- [x] 1.5 Add optional external-provider integration for `openai`, `anthropic`, and `google` that can rewrite only `summary` and `top_recommendation`, with safe fallback to local output when unavailable or invalid.

## 2. API and alert behavior

- [x] 2.1 Wire a protected `GET /decision` endpoint into `app/main.py` using the existing API-key guard and runtime state.
- [x] 2.2 Keep `/monitor`, `/metrics`, and `/alerts` backward compatible while ensuring decision guidance distinguishes `watch`/forecast states from formal alert history.
- [x] 2.3 Ensure cooldown-suppressed formal alerts still leave enough runtime evidence for `GET /decision` to expose elevated current risk.
- [x] 2.4 Harden API-key and payload-boundary paths with constant-time key comparison, safe malformed-header handling, and sanitized provider-status errors.

## 3. Reviewer bootstrap and dashboard

- [x] 3.1 Add a one-step reviewer bootstrap script that prepares a gitignored reviewer-local env file with owner-only read/write permissions, prompts for local vs external mode, collects provider/model/API-key only when needed, starts containers, runs smoke checks, and prints access details.
- [x] 3.2 Ensure bootstrap output prints raw monitoring API keys only for demo defaults; for non-demo keys, print only a safe reference to the reviewer-local env file/key name.
- [x] 3.3 Redesign `grafana/dashboard.json` around overall status, top recommendation, priority-ranked risk, forecast risk, evidence, recent formal alerts, transaction volume context, and a first-login guidance panel.
- [x] 3.4 Update dashboard contract checks and smoke scripts for the new decision endpoint queries, typed panel columns, and reviewer bootstrap validation.

## 4. Documentation and validation

- [x] 4.1 Update `README.md`, `SYSTEM_MAP.md`, `INVARIANTS.md`, and `docs/monitoring-methodology.md` to document the new endpoint, dashboard semantics, reviewer bootstrap, first-login details, and local-vs-external provider behavior.
- [x] 4.2 Add API tests for `GET /decision`, including auth enforcement, response shape, deterministic local output for known denied/failed/reversed spike windows, and the locked `normal/watch/act_now` state mapping.
- [x] 4.3 Add tests for forecast degradation, external-provider fallback, provider-status sanitization, and separation between predictive watch states and formal alert-history writes.
- [x] 4.4 Add validation coverage for the reviewer bootstrap path, including restricted reviewer-local env file permissions and sanitized terminal output for non-demo keys.
- [x] 4.5 Add validation coverage for smoke script integration and security-sensitive edge cases around malformed headers and reviewer-local env handling.
- [x] 4.6 Run the targeted test suite plus dashboard contract checks and fix any regressions uncovered by the results.
