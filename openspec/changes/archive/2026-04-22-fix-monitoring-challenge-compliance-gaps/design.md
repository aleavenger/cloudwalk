## Context

The current repository already provides a working anomaly engine, aggregate monitoring endpoint, decision guidance, Grafana dashboard, and one-click reviewer flow. The remaining gaps are challenge-compliance gaps rather than missing core infrastructure: formal alerts are only logged locally, the runtime does not offer a single-transaction ingestion contract, and reviewer-facing documentation still understates what the runtime does in some places and overstates manual setup in others.

The fix crosses multiple modules: backend settings/models/notifier logic, runtime state handling, reviewer Docker Compose services, smoke checks, and documentation/report artifacts. The solution must preserve the current dataset-replay flow and dashboard contracts while adding the missing prompt-aligned behavior additively.

## Goals / Non-Goals

**Goals:**
- Add real team-facing automatic notification delivery with truthful status reporting.
- Provide a prompt-aligned single-transaction ingestion endpoint without breaking `POST /monitor`.
- Keep one-click reviewer startup self-contained by provisioning a local demo notification target.
- Align README/report/contracts with actual runtime behavior and challenge mapping.

**Non-Goals:**
- Replace the current aggregate monitoring endpoint or migrate the dashboard to a new datasource contract.
- Introduce production-grade incident-management integrations beyond a generic webhook contract.
- Add persistent storage beyond the existing local files and in-memory runtime model.
- Build a full UI for reviewing delivered notifications.

## Decisions

### Use a dual-sink notifier: local log plus webhook
The backend will keep the existing aggregated log sink for traceability and add a webhook sink for team delivery. This closes the “notifications to teams” prompt gap without giving up the reviewer-friendly local audit log.

Alternatives considered:
- File log only: rejected because it does not satisfy team-facing delivery.
- SMTP/email: rejected because it adds configuration and infrastructure burden without improving local reviewer ergonomics.
- Slack-specific integration: rejected because the prompt does not require a vendor-specific notification path and a generic webhook is easier to demo locally.

### Add `POST /monitor/transaction` instead of changing `POST /monitor`
The aggregate endpoint already matches the dataset and current test/dashboard setup, so it should stay. A new additive event endpoint will accept a single transaction event, normalize it into a minute bucket, update the corresponding counts/auth-code tallies, and then reuse the existing anomaly engine and notifier flow.

Alternatives considered:
- Replace `POST /monitor` with event ingestion: rejected because it breaks the dataset replay contract and current tests.
- Rename the aggregate endpoint: rejected because it creates avoidable contract churn for reviewers and Grafana.
- Docs-only defense of the aggregate endpoint: rejected because it leaves the audit finding materially open.

### Provision a local mock notification receiver in the reviewer stack
The one-click reviewer runtime should demonstrate end-to-end delivery without depending on external services. A lightweight local receiver service can accept webhook posts, persist received payloads to a host-visible path, and give smoke checks a deterministic verification surface.

Alternatives considered:
- Require an external webhook URL: rejected because it weakens the reviewer experience and makes the demo incomplete by default.
- Provide only a manual receiver script: rejected because it adds setup steps and leaves the one-click flow incomplete.

### Report notification truth additively in alert history
The runtime currently uses a single `notification_status` field that reflects local reporting, not team delivery. The alert contract will keep that field for backward compatibility and add explicit team-delivery fields such as `team_notification_status` and `notification_channels` so the system can represent `sent`, `failed`, and `disabled` honestly.

Alternatives considered:
- Reinterpret `notification_status` to mean webhook delivery only: rejected because it would silently change the existing API contract.
- Remove the legacy field: rejected because it would create unnecessary breakage for current tests and dashboard/reporting assumptions.

## Risks / Trade-offs

- [More moving parts in the reviewer stack] -> Keep the mock receiver minimal, local-only, and smoke-tested through a single deterministic alert path.
- [Event endpoint can mutate baseline state minute by minute] -> Reuse the existing minute-bucket state update path so `POST /monitor` and `POST /monitor/transaction` converge on one evaluation flow.
- [Webhook failures may confuse reviewers] -> Surface explicit team notification status in alert history and document the demo target clearly in README/report output.
- [Contract growth can drift docs again] -> Update README, report, SYSTEM_MAP, INVARIANTS, and methodology in the same change set and add tests that assert the new fields and reviewer-flow behavior.

## Migration Plan

1. Add notifier/config/model support for webhook delivery and additive alert-history fields.
2. Add the transaction-event endpoint and reuse the existing runtime-state update/evaluation path.
3. Add the local mock receiver service plus compose/bootstrap/smoke wiring.
4. Update tests for API contracts, team notification behavior, and reviewer smoke expectations.
5. Sync README, report, and repo-governance docs to the new runtime truth.

Rollback is straightforward because the change is additive:
- disable webhook delivery by unsetting the webhook URL,
- stop calling `POST /monitor/transaction`,
- continue using the existing aggregate `/monitor` endpoint and local log trace.

## Open Questions

None. The change will use a generic webhook sink, a default local mock receiver in one-click mode, and an additive `POST /monitor/transaction` endpoint while preserving the current aggregate monitoring contract.
