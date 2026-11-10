# Compose startup audit

Source: user-reported docker compose up -d failure; live container logs and configuration inspection. The audit-uat registry contains no existing findings. Scope is the reported startup failure.

| ID | Finding | Severity | Classification |
| --- | --- | --- | --- |
| F-01 | docker/compose.yaml interpolates LANGSMITH_API_KEY with an empty default, overriding the key in service env_file | high | auto-fixable |

Evidence: docker-graph-1 exited 3 with License verification failed. A boolean-only inspection showed OPENAI_API_KEY present, LANGSMITH_API_KEY absent, and no cloud license key. The API stayed Created because graph health is a prerequisite. No credential values were printed.

Fix: remove only the LANGSMITH_API_KEY environment override; load the credential directly from ../.env. Preserve readiness dependencies, images, volumes, existing project-name customization and credentials. Add a synthetic Compose configuration regression test with an empty interpolation environment, from both root and docker working directories.

Execution was inline/sequential per skill spawn restriction.

Verification: two synthetic Compose tests pass. Running docker compose up -d --wait --wait-timeout 90 from docker/ exits 0, with all five services healthy. The graph and API health endpoints return HTTP 200. The complete offline Python suite passes (95 tests, 3 external tests deselected), with the existing LangChain community deprecation warning. No live model calls, image rebuilds, seed runs or volume removal occurred.

F-01: fixed. Existing unrelated changes, including the Compose LANGSMITH_PROJECT default customization, remain outside the fix commit.
