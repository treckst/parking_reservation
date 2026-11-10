---
phase: 01-persistent-grounded-policy-chat
plan: "07"
status: implemented_unverified
key-files:
  created: [src/parking/web/app.mjs, src/parking/web/styles.css, tests/web/chat.test.mjs]
requirements-completed: []
---

# Per-tab customer chat

Commit 992afef adds an injectable browser controller, per-tab session storage,
Web Lock claims to detach duplicated active tabs, immediate New chat, safe text
rendering and accessible controls. Pending replies disable Send while retaining
editable drafts. Recovery polls the existing request and never blindly repeats
an uncertain POST. Retry is shown only for proven failure; stale results from
an old chat are ignored.

Authored node:test cases cover draft retention/double send, lost acknowledgement
and stale results after New chat. No browser or JS checks were executed.

Known limitation: browser-restored session storage/cookies may reopen an old
conversation after all windows close. D-06 is not established. Without Web Locks,
the conservative fallback detaches on page load, so D-05 is not established on
those browsers either. The user skipped gates; these limits are documented
instead of asking for another decision or claiming the requirements passed.

## Self-Check: SKIPPED

Target-browser close/restore/refresh/duplicate-tab matrix remains unverified.
