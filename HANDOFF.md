# Handoff

State of the Descript reverse-engineering work on this branch, for whoever picks it up next.

## Done

| Area | Analysis | Pseudocode |
| --- | --- | --- |
| Underlord agent: skills, tools, protocol | [docs/descript-analysis/underlord/](docs/descript-analysis/underlord/) | [docs/pseudocode/underlord/](docs/pseudocode/underlord/) |
| Underlord on the wire (signed-in capture, 2026-10-22): protocol, SSE, Auto, @-context, skills, templates, undo | [observed-network.md](docs/descript-analysis/underlord/observed-network.md), [prompt-catalog.md](docs/descript-analysis/underlord/prompt-catalog.md), [skill-picker-and-opener.md](docs/descript-analysis/underlord/skill-picker-and-opener.md) | [transcript-model.md § selection as agent context](docs/pseudocode/transcript-model.md#selection-as-agent-context-descript-observed) |
| AI Tools panel catalog (every item → action, preset, paywall) | [docs/descript-analysis/ai-tools/](docs/descript-analysis/ai-tools/) | n/a |
| Smooth jump cuts | [ai-tools/smooth-jump-cuts.md](docs/descript-analysis/ai-tools/smooth-jump-cuts.md) | [smooth-jump-cuts.md](docs/pseudocode/smooth-jump-cuts.md) |
| Automatic multicam | [ai-tools/automatic-multicam.md](docs/descript-analysis/ai-tools/automatic-multicam.md) | [automatic-multicam.md](docs/pseudocode/automatic-multicam.md) |
| Publish / Write prompt actions | [ai-tools/prompt-actions.md](docs/descript-analysis/ai-tools/prompt-actions.md) | [youtube-titles-descriptions.md](docs/pseudocode/youtube-titles-descriptions.md) |
| Stock, GIPHY, AI image generation | n/a | [editor/stock-asset-providers.md § how Descript does it](docs/pseudocode/editor/stock-asset-providers.md#how-descript-does-it-for-comparison) |
| Timeline right-click, New layer menu, empty-scene overlay | n/a | [editor/layers.md § Descript menus](docs/pseudocode/editor/layers.md#descript-menus-mapped-to-actions-for-comparison) |
| Editor settings: room tone on gap clips, Smart transitions on new scenes, wordless media in script | [docs/descript-analysis/editor-settings/](docs/descript-analysis/editor-settings/) (signed-in results in [signed-in-gaps.md](docs/descript-analysis/editor-settings/signed-in-gaps.md)) | [docs/pseudocode/editor-settings/](docs/pseudocode/editor-settings/) |
| Public API agent job (`/v1/jobs/agent`) | [docs/api-notes.md](docs/api-notes.md) | [docs/pseudocode/underlord-agent-job.md](docs/pseudocode/underlord-agent-job.md) |

**Sources.**

- **Public build.** `react19/9a29d61183bce669600a9dd9a1f8588d708becac`, all 145 chunks.
- **Signed build.** `react19/a7c779e…` (app 153.0.4): chunks app, 5433, 8211, 9105, 9476 and 1212, unpacked with Wakaru.
- **Hunter's capture.** One signed-in mitm capture of his own projects, taken 2026-10-22.

Raw flows, JS, Wakaru modules and the capture index stay on the research box (`/workspace/polish-clips-rea-research/decompile/`). The docs carry descriptions, field names and paraphrase only: no IDs, tokens, signed URLs or prompt text.

## Unfinished

| Gap | Where it is tracked | What would close it |
| --- | --- | --- |
| "Want me to improve this video?" opener: exact trigger and copy source | [skill-picker-and-opener.md](docs/descript-analysis/underlord/skill-picker-and-opener.md) | A capture of a fresh project load with the agent sidebar auto-opening |
| The 11th skill-picker row versus the catalog | same | A screenshot plus a capture of a picker run |
| Plan-approval wire format; the `undo_changes` result; cloud-agent events | [underlord/signed-in-gaps.md](docs/descript-analysis/underlord/signed-in-gaps.md) | A planning turn ("plan first, then…"), and an account with the cloud flag |
| Publish/Write, image generation, Smooth jump cuts, multicam: nothing on the wire yet | [ai-tools/](docs/descript-analysis/ai-tools/) | The recipe at the end of the underlord signed-in gaps page |
| GIPHY traffic | [stock-asset-providers.md](docs/pseudocode/editor/stock-asset-providers.md) | A capture filter that includes `api.giphy.com` |
| Quick design (`START_QUICK_DESIGN`, window-dressing preset), Write a script params, Smart zoom | [ai-tools/README.md](docs/descript-analysis/ai-tools/README.md) | Decompile the window-dressing module in 9105 (its option labels were seen) |
| Timeline handlers for Add volume keyframe, Dip volume, Auto-level | [layers.md](docs/pseudocode/editor/layers.md) | Trace the timeline action module in 8211 |
| A typed inline script delete on the wire | [transcript-model.md](docs/pseudocode/transcript-model.md) | A capture of a Backspace edit in the script |
| Wordless-media font file; room tone server algorithm; Smart transitions property list | [editor-settings/signed-in-gaps.md](docs/descript-analysis/editor-settings/signed-in-gaps.md) | Global CSS / font fetch; an asset download; a layout change across scenes |

## Backlog

- **Highlight scoring for short-form clips (Opus-style "find highlights"). Not started; do not implement yet.**
  - **What exists in Descript.** The AI Tools items Find highlights (`find-highlights`), Create clips (`make-clips`, agent-routed) and Create highlight reel (`make-highlight-reel`; params `targetDuration`, `templateDetails`) ([prompt-actions.md](docs/descript-analysis/ai-tools/prompt-actions.md)). The legacy route is `POST /projects/{id}/ai_actions/clips`, and it has its own empty-result error. `highlights` is one of the top tags across the 32 public agent templates ([observed-network.md](docs/descript-analysis/underlord/observed-network.md)).
  - **What the capture showed.** Hunter's "make 3 short clips for tiktok" used no highlight endpoint. The model picked the clips itself from one `query_script_markdown` read, then called `copy_script_segments` ×3 ([prompt-catalog.md](docs/descript-analysis/underlord/prompt-catalog.md)). The `find-highlights` sub-skill has no client body and was never loaded.
  - **Our stub.** `find_highlights` in [docs/pseudocode/underlord/create-clips-workflow.md](docs/pseudocode/underlord/create-clips-workflow.md).
  - **To do later.** Add a scoring pass: a hook in the first 3 s, a self-contained arc, sentiment and energy peaks, speaker change, and a length fit to the platform. Rank the candidate windows, then hand the top N to `copy_script_segments`-style clip creation.
