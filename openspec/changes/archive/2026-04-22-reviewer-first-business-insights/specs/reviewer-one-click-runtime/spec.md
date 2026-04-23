## MODIFIED Requirements

### Requirement: Reviewer bootstrap SHALL support provider-mode selection safely
The reviewer bootstrap flow SHALL let the reviewer choose between local decision guidance and optional external-provider-backed narrative enhancement without weakening the local-safe defaults.

#### Scenario: Reviewer bootstrap prefers external mode
- **WHEN** the reviewer starts the guided bootstrap flow
- **THEN** the provider-mode prompt SHALL default to `external` rather than `local`

#### Scenario: Reviewer selects local mode
- **WHEN** the reviewer chooses local mode
- **THEN** the bootstrap flow SHALL configure the stack without requiring any external provider API key and SHALL describe local mode as a deterministic fallback with less narrative polish rather than a broken mode

#### Scenario: Reviewer selects external mode
- **WHEN** the reviewer chooses external mode
- **THEN** the bootstrap flow SHALL offer the provider choices `openai`, `anthropic`, and `google`, collect the provider model and API key, and configure the runtime accordingly

#### Scenario: Missing external API key falls back to local mode
- **WHEN** the reviewer chooses external mode but does not provide a valid API key
- **THEN** the bootstrap flow SHALL fall back to local mode rather than leaving the runtime half-configured

### Requirement: Reviewer bootstrap SHALL validate and message the environment
The reviewer bootstrap flow SHALL tell the reviewer what is available after startup and confirm the environment is working before declaring success.

#### Scenario: Bootstrap prints reviewer-facing provider guidance
- **WHEN** the reviewer bootstrap finishes successfully
- **THEN** it SHALL print the selected provider mode, explain whether richer external narrative is active, and explain the local deterministic fallback when external mode is unavailable

#### Scenario: Bootstrap avoids exposing non-demo API keys in terminal output
- **WHEN** the reviewer bootstrap completes with non-demo API-key values
- **THEN** it SHALL avoid printing raw API-key values and SHALL print only a safe reference to where that key is stored
