# Phase 1: Persistent Grounded Policy Chat - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 01-CONTEXT.md; this log preserves alternatives and user selections.

**Date:** 2026-11-10
**Phase:** 01-persistent-grounded-policy-chat
**Areas discussed:** Answers and sources, Conversation continuity, Unclear or unsupported questions, Chat interaction and recovery

**Mode:** Interactive discussion with plain-text numbered choices.
**Selection:** The user selected all four areas, confirmed each area was complete, and approved saving the final context.

---

## Answers and sources

### 1. What language should the assistant use?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Match the customer's message (recommended) — English questions get English replies, Polish questions get Polish replies. | Yes |
| 2 | English only — consistent language throughout the demo. |  |
| 3 | Polish only — Polish replies regardless of the question's language. |  |

**User's choice:** Match the customer's message: English questions get English replies, Polish questions get Polish replies.

### 2. How detailed should answers be?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Concise by default (recommended) — a direct answer in 2–4 sentences, with bullets when useful. | Yes |
| 2 | Detailed by default — explain the rule, conditions, and exceptions. |  |
| 3 | Minimal — one sentence unless the customer asks for more. |  |

**User's choice:** Concise by default: a direct answer in 2–4 sentences, with bullets when useful.

### 3. How should supporting sources appear?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Small Sources section (recommended) — document title and page number below the answer. |  |
| 2 | Inline citations — source references beside the claims they support. | Yes |
| 3 | On request only — keep sources hidden unless the customer asks. |  |

**User's choice:** Inline citations: source references beside the claims they support.

### 4. What tone should the assistant use?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Friendly and straightforward (recommended) — natural, polite, and practical. | Yes |
| 2 | Formal — neutral, professional wording. |  |
| 3 | Casual — relaxed and conversational. |  |

**User's choice:** Friendly and straightforward: natural, polite, and practical.

**Area completion:** User chose the next area; for the final area, user approved saving the phase context.

---

## Conversation continuity

### 1. When the customer refreshes the page, what should happen?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Restore the current conversation (recommended) - show its messages and continue the same thread. | Yes |
| 2 | Show a fresh chat - start a new thread; keep the previous thread stored. |  |

**User's choice:** Restore the current conversation: show its messages and continue the same thread.

### 2. User-specified checkpoint implementation constraint

| Option | Description | Selected |
|--------|-------------|----------|
| User-specified | Use SqliteSaver with a separate SQLite database for graph checkpoints, distinct from the bookings database. Create the connection outside the graph and access it through a local variable/closure; do not pass the connection as runtime context. This supersedes research that recommended only the default PostgreSQL checkpointer. Verify compatibility with Agent Server custom-checkpointer async/conformance requirements; do not silently substitute another saver. | Yes |

**User's choice:** Use SqliteSaver with a separate SQLite database for graph checkpoints, distinct from the bookings database. Create the connection outside the graph and access it through a local variable/closure; do not pass the connection as runtime context. This supersedes research that recommended only the default PostgreSQL checkpointer. Verify compatibility with Agent Server custom-checkpointer async/conformance requirements; do not silently substitute another saver.

**Notes:** The latest user constraint supersedes the earlier research default of PostgreSQL-only checkpoints. Agent Server custom-checkpointer async/conformance compatibility remains a setup gate; no saver substitution was authorized.

### 3. After closing and reopening the same browser, should chat resume?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Resume until New chat is chosen (recommended). |  |
| 2 | Resume only within 24 hours. |  |
| 3 | Start a fresh conversation. | Yes |

**User's choice:** Start a fresh conversation after the browser is closed and reopened; refreshing a page continues the current thread.

### 4. When the customer opens another tab, what should happen?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Start a separate conversation (recommended) - each tab has its own thread. | Yes |
| 2 | Share the current conversation - both tabs show and continue the same thread. |  |

**User's choice:** Start a separate conversation: each tab has its own thread.

### 5. How should New chat behave?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Start immediately (recommended) - open a fresh thread and leave the previous thread stored. | Yes |
| 2 | Ask for confirmation first - then start a fresh thread, keeping the previous one stored. |  |

**User's choice:** Start immediately: open a fresh thread and leave the previous thread stored.

**Area completion:** User chose the next area; for the final area, user approved saving the phase context.

---

## Unclear or unsupported questions

### 1. If a policy question depends on the facility, but none is clear from the conversation, what should the assistant do?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Ask which facility (recommended) - avoid assuming the wrong location. |  |
| 2 | Give only rules shared by all facilities - explain that location-specific details need clarification. |  |
| 3 | Briefly compare all four facilities. | Yes |

**User's choice:** Briefly compare all four facilities.

### 2. If the documents support only part of a comparison or question, how should the assistant respond?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Answer the supported parts (recommended) - cite them and clearly mark the rest as unavailable. | Yes |
| 2 | Return only the no-information response - avoid giving a partial answer. |  |

**User's choice:** Answer the supported parts with citations and clearly mark the rest as unavailable.

### 3. When nothing in the documents supports an answer, what should happen?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | State the limit and offer a relevant alternative (recommended). |  |
| 2 | Give only a brief no-information response without suggestions. |  |
| User-specified | User specified a retrieval refinement: ask the LLM to rewrite the search query to improve semantic retrieval while preserving the original meaning; retrieve and reassess once. If still unsupported, tell the customer their question is unsupported and ask for a new question. This refines the earlier no-information fallback; it does not authorize inventing evidence or changing customer intent. | Yes |

**User's choice:** User specified a retrieval refinement: ask the LLM to rewrite the search query to improve semantic retrieval while preserving the original meaning; retrieve and reassess once. If still unsupported, tell the customer their question is unsupported and ask for a new question. This refines the earlier no-information fallback; it does not authorize inventing evidence or changing customer intent.

**Notes:** The assistant reflected a single meaning-preserving query rewrite, retrieval, and reassessment; the user then chose a silent retry and confirmed moving to the next area.

### 4. Should the query-rewrite retry be silent or visible?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Silent (recommended) - show only the final answer or unsupported response. | Yes |
| 2 | Visible - briefly show Trying a different search wording while retrying. |  |

**User's choice:** Silent: show only the final supported answer or unsupported response.

**Area completion:** User chose the next area; for the final area, user approved saving the phase context.

---

## Chat interaction and recovery

### 1. While the assistant is working, what should the customer see?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | A simple Checking indicator (recommended), then the complete answer after the output guardrail finishes. |  |
| 2 | Brief progress labels such as Searching documents and Checking the answer, followed by the complete checked response. |  |
| User-specified | Customer should not see what the assistant is doing. Show only the final checked reply, with no progress labels or internal steps. | Yes |

**User's choice:** Customer should not see what the assistant is doing. Show only the final checked reply, with no progress labels or internal steps.

**Notes:** The user overrode both proposed progress-display options. The confirmed behavior shows only the final checked reply, without progress labels or internal steps.

### 2. While waiting, should the customer be able to type?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Allow typing, but disable Send (recommended). | Yes |
| 2 | Disable both typing and Send until the reply arrives. |  |

**User's choice:** Allow typing, but disable Send: customers can draft their next message.

### 3. If a request temporarily fails, how should recovery work?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Show a brief error and a Retry button (recommended), keeping message and conversation intact. | Yes |
| 2 | Show a brief error and ask the customer to resend the message. |  |

**User's choice:** Show a brief error and a Retry button; keep the message and conversation intact.

### 4. If the page refreshes or the connection drops before a reply arrives, how should recovery work?

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Recover the existing request (recommended) and show its result without resubmitting. | Yes |
| 2 | Show Retry and let the customer choose when to resume the request. |  |

**User's choice:** Recover the existing request and show its result without submitting the question again.

**Area completion:** User chose the next area; for the final area, user approved saving the phase context.

---

## Agent Discretion

No additional product choices were explicitly delegated. Implementation mechanics remain with research/planning within the decisions in 01-CONTEXT.md.

## Deferred Ideas

None. Existing later-phase SQL availability, bookings, administrator decisions, and cancellation retain their approved roadmap ownership.

## Final Confirmation

The user selected option 1: Save the Phase 1 context for research and planning. No implementation or phase plan was created during this discussion.
