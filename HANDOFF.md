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
| Feature designs (2026-10-22): visual descriptions, auto audio sync, Find Highlights + Make Clips, publish metadata, highlight reel, media montage, animated story | [docs/features/](docs/features/README.md) (evidence tags per claim; see the table below) | [visual-descriptions](docs/pseudocode/visual-descriptions.md), [auto-audio-sync](docs/pseudocode/auto-audio-sync.md), [find-highlights](docs/pseudocode/find-highlights.md), [publish-metadata](docs/pseudocode/publish-metadata.md), [highlight-reel](docs/pseudocode/highlight-reel.md), [media-montage](docs/pseudocode/media-montage.md), [animated-story](docs/pseudocode/animated-story.md) |

**Feature designs: evidence vs design.** Every spec is our own design. Descript evidence is cited only where it shaped a decision.

| Feature | Evidence-backed parts | Design-only parts |
| --- | --- | --- |
| Visual descriptions | Descript's per-asset artifact, entry fields, heavy-read and oversized guard, wait tool, placeholder-at-import (observed-network, decompiled) | Shots, sampling, VLM schema, off-topic relevance, index, UI, costs |
| Auto audio sync | Descript's autosync preconditions, result fields, no-op reasons, one-commit apply, 8-min agent timeout (decompiled) | DSP pipeline, drift, session graph, silent-clip fallback, nudge UX |
| Find Highlights + Make Clips | Hunter's B3 capture (model-picked ranges, no scoring), presets (decompiled), OpusClip score/sub-score/API shapes (public-research) | Candidate generation, rubric + fusion score, dedupe, snapping, reframe/hook/B-roll, title/hook/description packaging |
| Publish metadata | Platform limits and ranking statements, dated 2026-10-22 (public-research) | Generator, validation, judge, thumbnails, A/B loop |
| Highlight reel | `make-highlight-reel` params (decompiled) | Solver, ordering, transitions |
| Media montage, animated story | Descript generation tool shapes only (decompiled) | Everything else |

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
| Feature-design open questions: Instagram hashtag cap (5 vs API 30; do comment tags count?), TikTok hashtag cap (reported 5, undocumented), Facebook caption limit (unpublished), Instagram reach for Reels over 3 min, custom Shorts thumbnails | [platform-profiles.md](docs/features/publish-metadata/platform-profiles.md) | Re-check the sources quarterly; test posts on a sandbox account |
| Descript visual-description artifact bodies and sync server internals were not captured | [visual-descriptions](docs/features/visual-descriptions/README.md), [auto-audio-sync](docs/features/auto-audio-sync/README.md) | Not needed for our design. Optional: an asset download in a capture |
| Fusion weights, thresholds and sweet-spot durations are hand-set | [find-highlights](docs/features/find-highlights/README.md#eval--metrics) | Build the 40-video eval set; fit from keep/discard feedback |

## Backlog

- ~~**Highlight scoring for short-form clips (Opus-style "find highlights").**~~ **Designed 2026-10-22.** See [docs/features/find-highlights/](docs/features/find-highlights/README.md) and [pseudocode](docs/pseudocode/find-highlights.md). It covers candidate windows, an LLM rubric (hook/flow/value/trend), multimodal fusion to a 0–99 score, dedupe, sentence/silence snapping, platform durations, 9:16 reframe, and title/hook/description per platform. The Descript evidence (presets, legacy clips route, B3 capture showing model-picked ranges with no scoring) is in the spec's Evidence section. Next step: build the MVP listed there.
