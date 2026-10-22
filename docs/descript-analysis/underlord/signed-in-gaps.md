# Underlord: signed-in gaps

Descript blocks logins from the box, so these need a HAR recorded by Hunter. **Recipe:** open a project in Chrome, DevTools → Network → Preserve log; filter `agent|cloudagent|feature|flags|agent-instructions`. Run three turns: (a) "remove filler words and tighten pauses", (b) "make 3 vertical clips from this", approving the plan, (c) roll back turn (a). Save as HAR with content.

| # | Gap | What the HAR answers |
| --- | --- | --- |
| 1 | Resolved feature-flag values for the account | Local or cloud mode (`underlord-use-cloud-agent`), harness id, `agent-model-*`, loop limits, skills UX flags |
| 2 | `/agent/completions` real request | Full system prompt as sent, tool list after filters, model id, reasoning settings |
| 3 | `/agent/completions` SSE body | Exact chunk shape, reasoning detail types, usage fields |
| 4 | Cloud SSE events | Payloads of `tool_call_*` and how document changes reach the client (patch, commit ref or reload) |
| 5 | Server-only skills | Bodies of the sub-skills referenced but absent from the client (see [skill-graph.md](skill-graph.md)); `load_skill` responses |
| 6 | Credits | Credit deltas per turn and per generation tool (account usage endpoint before and after) |
| 7 | Plan approval | The plan message format and the approval message on the wire |
| 8 | Rollback | The rollback request and the `rolledBackAt` fields in chat detail |
| 9 | Post-turn verification | Whether it runs for this account, and what the follow-up turn looks like |
| 10 | Drive admin groups | Response that carries disabled feature groups (team account only) |
