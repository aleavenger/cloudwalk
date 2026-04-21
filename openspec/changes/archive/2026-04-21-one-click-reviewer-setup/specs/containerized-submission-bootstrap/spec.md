## ADDED Requirements

### Requirement: API container SHALL generate required derived artifacts before serving traffic
The containerized API startup flow SHALL generate the checkout anomaly CSV outputs and checkout chart assets before launching the FastAPI application.

#### Scenario: Derived artifacts are created during startup
- **WHEN** the API container starts in the one-click runtime
- **THEN** it SHALL generate the expected report CSV outputs and checkout chart assets before the API begins serving requests

#### Scenario: Generated outputs remain visible to the reviewer
- **WHEN** the one-click stack finishes startup
- **THEN** the generated report and chart files SHALL be present in reviewer-visible host paths rather than only inside the container filesystem

#### Scenario: Startup fails fast on bootstrap errors
- **WHEN** artifact generation fails during container startup
- **THEN** the API container SHALL exit with a failure rather than silently starting in a partial state

### Requirement: One-click bootstrap SHALL remain reproducible from repository state
The one-click startup flow SHALL rely only on repository-tracked inputs and environment values documented in the repository.

#### Scenario: Reviewer does not need to run prep scripts manually
- **WHEN** a reviewer uses the documented Docker Compose path
- **THEN** the reviewer SHALL not need to invoke the analysis or chart-generation scripts as separate manual steps

#### Scenario: Service startup waits for API readiness
- **WHEN** the reviewer stack is started
- **THEN** dependent readiness checks and smoke verification SHALL wait for the API health endpoint to report healthy before treating the stack as ready
