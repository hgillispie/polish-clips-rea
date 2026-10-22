# Handoff

State of the Descript reverse-engineering work on this branch, for whoever picks it up next.

## Done

| Area | Analysis | Pseudocode |
| --- | --- | --- |
| Underlord agent: skills, tools, protocol | [docs/descript-analysis/underlord/](docs/descript-analysis/underlord/) | [docs/pseudocode/underlord/](docs/pseudocode/underlord/) |
| Editor settings: room tone on gap clips, Smart transitions on new scenes, wordless media in script | [docs/descript-analysis/editor-settings/](docs/descript-analysis/editor-settings/) | [docs/pseudocode/editor-settings/](docs/pseudocode/editor-settings/) |
| Public API agent job (`/v1/jobs/agent`) | [docs/api-notes.md](docs/api-notes.md) | [docs/pseudocode/underlord-agent-job.md](docs/pseudocode/underlord-agent-job.md) |

Source: build `react19/9a29d61183bce669600a9dd9a1f8588d708becac`. All 145 public chunks in that build's webpack runtime were downloaded (41 on 2026-10-19, 104 on 2026-10-22), with Wakaru-unpacked modules kept on the research box only (`/workspace/polish-clips-rea-research/decompile/`). Docs carry descriptions, not code or prompt text.

## Waiting on Hunter (signed-in HARs)

Descript blocks logins from the research box. The capture recipes are in:

- [docs/descript-analysis/underlord/signed-in-gaps.md](docs/descript-analysis/underlord/signed-in-gaps.md): flags, real system prompt and tool list, SSE bodies, server-only sub-skills, credits.
- [docs/descript-analysis/editor-settings/signed-in-gaps.md](docs/descript-analysis/editor-settings/signed-in-gaps.md): the room tone server algorithm and asset, saved document shapes, agent-created scenes and Smart transitions, the wordless-media font.

## Backlog

- Short-form clip picking (Opus-style "find highlights"): Descript's `find-highlights` sub-skill has no client body, so it is server-side or model-only. Our stub is `find_highlights` in [docs/pseudocode/underlord/create-clips-workflow.md](docs/pseudocode/underlord/create-clips-workflow.md).
