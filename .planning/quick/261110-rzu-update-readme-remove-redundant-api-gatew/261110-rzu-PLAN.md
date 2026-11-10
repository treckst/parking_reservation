# README, UI gateway and deployment cleanup

1. Replace the historical README with current behavior, supported routes, setup, storage and testing instructions grounded in the source. Review every Gateway method/caller; retain UI submission ownership/idempotency and remove redundant terminal-run processing. Verify the affected API/recovery behavior.
2. Build the current graph image with the LangGraph CLI, rebuild the API from that image, restart Docker Compose without deleting persistent data, and verify image identity, graph/UI health and absence of admin API code. Record any external startup dependency that remains unavailable.

Acceptance: README describes automatic admin subgraph and real environment/setup paths; gateway has no admin orchestration and retains safe polling/recovery; tests pass; the running graph uses the newly built image and Compose is healthy, or an independently verified external blocker is reported accurately.

Execution: inline under the skill's no-automatic-spawn adapter. Preserve unrelated pre-existing working-tree changes.
