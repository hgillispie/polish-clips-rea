# Polish Clips feature designs

These are product and algorithm specs for features we build ourselves. They are **not** clones of Descript. Hunter's direction (2026-10-22) was to design best-in-class versions. Descript evidence we already hold is linked only where it helps, and public research is cited by URL.

Each feature folder has a `README.md` spec with these sections: user story, UX, inputs/outputs, algorithm, models/APIs (with options), data model, edge cases, eval/metrics, MVP vs later. Each feature also has a matching pseudocode file under [../pseudocode/](../pseudocode/), written so Claude Code can implement it directly.

## Evidence tags

| Tag | Meaning |
| --- | --- |
| **observed-network** | Seen in Hunter's signed-in Descript capture, 2026-10-22 ([../descript-analysis/underlord/observed-network.md](../descript-analysis/underlord/observed-network.md)) |
| **decompiled** | Read from a Wakaru-unpacked module of the signed Descript build. Described in our own words; no code copied |
| **static-help** | A vendor's public help page or docs |
| **public-research** | Papers, platform creator docs, vendor blogs. Each one is cited with a URL and the date we checked it |
| **design** | Our own decision. These are the default for everything in this folder |

Platform claims change often. Every platform number carries a "checked" date, and anything we could not confirm is marked **uncertain**.

## Features

| # | Feature | Spec | Pseudocode | Depends on |
| --- | --- | --- | --- | --- |
| 1 | Auto audio sync | [auto-audio-sync/](auto-audio-sync/README.md) | [auto-audio-sync.md](../pseudocode/auto-audio-sync.md) | none (supersedes [editor/audio-waveform-align.md](../pseudocode/editor/audio-waveform-align.md)); feeds [automatic-multicam.md](../pseudocode/automatic-multicam.md) |
| 2 | Find Highlights + Make Clips/Shorts/Reels | [find-highlights/](find-highlights/README.md) | [find-highlights.md](../pseudocode/find-highlights.md) | 7, 4 (publish profiles), transcript, captions, reframe |
| 3 | Highlight Reel | [highlight-reel/](highlight-reel/README.md) | [highlight-reel.md](../pseudocode/highlight-reel.md) | 2 |
| 4 | Publish metadata generator | [publish-metadata/](publish-metadata/README.md) ([platform-profiles.md](publish-metadata/platform-profiles.md)) | [publish-metadata.md](../pseudocode/publish-metadata.md) | transcript, 7 |
| 5 | Create media montage | [media-montage/](media-montage/README.md) | [media-montage.md](../pseudocode/media-montage.md) | 7, beat tracking |
| 6 | Generate an animated story | [animated-story/](animated-story/README.md) | [animated-story.md](../pseudocode/animated-story.md) | image/video gen, TTS, captions |
| 7 | Visual descriptions (visual track) | [visual-descriptions/](visual-descriptions/README.md) | [visual-descriptions.md](../pseudocode/visual-descriptions.md) | shot detection, VLM |

Build order (design): **7 → 1 → 2 → 4 → 3 → 5 → 6**. The visual track and publish profiles are shared foundations: clip scoring (2), packaging (2, 4), montage shot choice (5) and agent tools all read them.

## Shared conventions (design)

- **Time.** Every range is in **source seconds** of one media asset, `{media_id, start_s, end_s}`. A ranking is only mapped to composition time when it is applied (see [../pseudocode/timeline-model.md](../pseudocode/editor/timeline-model.md)).
- **Analysis artifacts.** These are per-asset and immutable, keyed by `(media_id, kind, version, params_hash)`:
  - `transcript` (words + speakers, [../pseudocode/transcript-model.md](../pseudocode/transcript-model.md))
  - `audio_features` (loudness, onsets, chroma, events)
  - `shots`
  - `visual_track` (feature 7)
  - `faces`/`tracks`
  - `embeddings`

  A feature reads artifacts and never recomputes one that already exists. Descript keeps the same kind of per-asset artifact list: `visual_descriptions`, `visual_embeddings`, `transcript_embeddings`, `energies`, `diarization`, `loudnorm`, `media_classification` (**decompiled**).
- **Jobs.** Long work runs as a job with states `queued → running → done | failed | canceled`, progress 0..1, and partial results. Agent tools wait with a timeout and return "still running" rather than blocking forever. Descript's autosync agent tool gives up after 8 minutes and tells the user to run it from the UI (**decompiled**).
- **Undo.** Every applied edit is one undoable commit with a human label.
- **Cost.** Every model call goes through one `ModelRouter` with per-feature budgets, caching by input hash, and a dry-run cost estimate shown before large jobs.
