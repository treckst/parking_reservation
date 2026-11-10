---
quick_id: 261110-llb
status: planned
---

# English-only application with structured language gate

1. Add a strict structured-output English-language decision node before safety, intent, retrieval and reservation execution. Reject non-English, mixed-language and unclear requests with a fixed English reply; preserve names, codes and booking details in English requests.
2. Remove Polish response branches and language selection from application prompts and schemas; convert supported test cases to English and document the entry gate.
3. Run offline Python and browser-controller regression tests, including rejected-turn isolation and subsequent English recovery. Commit only task-owned changes and record completion in STATE.md.

Execution runs inline under the skill's Codex fallback. Existing unrelated workspace edits remain untouched. Historical planning records and existing fixture data are preserved.
