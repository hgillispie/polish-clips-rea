# Underlord: signed-in gaps

**Status 2026-10-22.** Hunter's capture answered most of these; the details are in [observed-network.md](observed-network.md). *Open* rows still need another capture.

Descript blocks logins from the box, so these need a HAR recorded by Hunter. **Recipe:** open a project in Chrome, DevTools → Network → Preserve log; filter `agent|cloudagent|feature|flags|agent-instructions`. Run three turns: (a) "remove filler words and tighten pauses", (b) "make 3 vertical clips from this", approving the plan, (c) roll back turn (a). Save as HAR with content.

| # | Gap | What the HAR answers | Result |
| --- | --- | --- | --- |
| 1 | Resolved feature-flag values for the account | Local or cloud mode (`underlord-use-cloud-agent`), harness id, `agent-model-*`, loop limits, skills UX flags | **Closed.** Local mode (`underlord-use-cloud-agent` false). Auto = `default-v2-agent-harness` `mammoth-auto` → harness `mammoth-glm52-sonnet55-plain-text`, model `@preset/glm-5-2`. Skills UX flags on |
| 2 | `/agent/completions` real request | Full system prompt as sent, tool list after filters, model id, reasoning settings | **Closed.** Two cached system-prompt parts (about 35.5k characters; section list only), 72 tools, no sampling or reasoning params on the client |
| 3 | `/agent/completions` SSE body | Exact chunk shape, reasoning detail types, usage fields | **Closed.** OpenRouter-style `chat.completion.chunk` with `reasoning` / `reasoning_details` deltas and a final `usage` that includes `cost` |
| 4 | Cloud SSE events | Payloads of `tool_call_*` and how document changes reach the client (patch, commit ref or reload) | *Open.* Cloud mode is not used by this account |
| 5 | Server-only skills | Bodies of the sub-skills referenced but absent from the client (see [skill-graph.md](skill-graph.md)); `load_skill` responses | **Narrowed.** `create-clips` and `ask-underlord-for-suggestions` load with no network request (client bodies). The `find-highlights` family was never loaded. `/agent-instructions/{id}/content` was never fetched |
| 6 | Credits | Credit deltas per turn and per generation tool (account usage endpoint before and after) | **Narrowed.** The per-step `usage.cost` is visible; the credit conversion and usage endpoint are *open* |
| 7 | Plan approval | The plan message format and the approval message on the wire | *Open.* No plan was entered (`isPlanning` false throughout) |
| 8 | Rollback | The rollback request and the `rolledBackAt` fields in chat detail | **Narrowed.** After a stopped turn, undo was five editor `EDITOR/DOCUMENT/UNDO` commits. `undo_changes` was offered but never called; no rollback request was seen |
| 9 | Post-turn verification | Whether it runs for this account, and what the follow-up turn looks like | *Open.* No visible extra verification step; flags not checked in detail |
| 10 | Drive admin groups | Response that carries disabled feature groups (team account only) | *Open.* Personal account |


## Still open after the capture

- Plan-approval message format, cloud-agent events, and the `undo_changes` tool result shape.
- The exact trigger and copy source of the "Want me to improve this video?" opener ([skill-picker-and-opener.md](skill-picker-and-opener.md)).
- The 11th skill-picker row versus the 11-entry catalog.
- Any Publish/Write action, image generation, GIPHY or Smooth jump cuts on the wire. The decompiled flows are in [../ai-tools/](../ai-tools/).
- **Recipe for the next capture:** run Draft a title, Smooth jump cuts (findFirst), Automatic multicam on a 2-camera project, Generate image, and one GIPHY insert. Then click "Improve this video" and pick one skill from the `/` picker. Keep the capture filter wide enough to include `api.giphy.com`.
