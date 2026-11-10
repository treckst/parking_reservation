---
quick_id: 261110-llb
status: complete
commit: 1e246a6
---

# English-only application with structured language gate

Added `LanguageDecision(is_english: bool)` and the `check_language` node using
LangChain strict JSON-schema structured output. Only a positive decision reaches
the input safety guard, intent classifier and policy/reservation/admin subgraphs.
Negative decisions produce a fixed English rephrase request and end the turn.
Provider or schema failures propagate without downstream execution. English
requests may contain names, codes, plates, timestamps and details-only follow-ups.

Removed Polish reply branches and language detection from the safety guard;
restricted intent language to English. All answer, fallback, booking and summary
prompts/replies use English. Converted supported corpus and tokenizer examples to
English and updated UI guidance and operator documentation. Preserved fixture
data, stored historical conversations and historical planning records.

Validation: 83 offline Python tests passed, 3 deployed checks deselected; all
3 JavaScript controller tests passed. Regression tests cover rejection without
retrieval/writes, strict schema/provider failure, retained evidence/drafts and a
subsequent English turn. The initial sandbox run could not load NumPy's DLL;
the authorized unsandboxed run passed. One new test initially supplied an
unnormalized draft fixture; it was corrected to the actual BookingDetails schema.
The suite reports one pre-existing langchain-community deprecation warning.
Source/tests/docs scan found no remaining Polish content or language selection.

Implementation commit: `1e246a6`. No live model calls or container rebuild ran;
running containers need rebuilding to use the updated source. Execution stayed
inline per the skill's Codex fallback. Unrelated existing edits were excluded.
