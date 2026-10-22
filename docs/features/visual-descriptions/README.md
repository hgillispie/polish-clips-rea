# Visual descriptions (the visual track)

**Priority: high.** The agent cannot see. Today it edits from the transcript alone, plus one screenshot at a time ([../../descript-analysis/underlord/prompt-catalog.md](../../descript-analysis/underlord/prompt-catalog.md), B3/B4). That fails whenever the picture and the words disagree:

- shop B-roll with no speech
- a mechanic doing a brake job while chatting about the weekend
- a screen recording where the narration lags the clicks
- a cooking clip where the key moment is silent

The **visual track** is a time-coded, searchable record of what is on screen. It sits next to the transcript, and every feature and the agent can read it.

## User stories

- *As a creator*, I can type "find where he torques the lug nuts" and land on the shot, even though nobody says "lug nuts".
- *As a creator*, I can ask the agent to "use the close-ups of the welding as B-roll over the intro". It finds them by what is shown, not what is said.
- *As a creator*, clip suggestions skip the 4 minutes where the talk is off-topic, unless the visuals there are the point (the repair itself).
- *As the agent*, I can ask what happens on screen between two times, in a few hundred tokens rather than with 12 screenshots.

## What the capture showed (observed-network, decompiled)

**Hunter's prompts.** He asked two questions about this (prompt catalog B6, B7). The agent answered each one with `search_help` alone. It said that Wordless media is not a visual description, that visual descriptions are a separate feature, and that they are not exported. Nothing was generated during those turns.

**Storage on the wire (observed-network).** Descript keeps visual descriptions as **one JSON artifact per media asset**:
- `content_type: visual_descriptions`, `file_extension: json`
- Status is first `placeholder` with size 0, and later `completed`
- Five assets ranged from about 10 KB to 68 KB
- The placeholder appears at import, so description runs in the background without being asked for

**Entry shapes (decompiled).**
- A video entry is `{description, start_time, end_time, source}`, where `source ∈ entity | setting | foreground_event | background_event`.
- An image entry is one `{overall_summary}`.

**How the agent reads it (decompiled).**
- It never sees the JSON by default. `query_media_library_v2` and `query_tracks_v2` treat `visualDescriptions` as a **heavy property** that must be requested explicitly and narrowed by range or track.
- An oversized request comes back as `{status: "oversized", estimatedTokens, maxAllowedTokens, guidanceMessage}` instead of the data.
- The scene-content builder can attach `sceneVisualDescriptions`, keyed by visual layer name, to each scene.
- `wait_for_visual_descriptions {folder_name?, media_ref_ids?}` blocks until the artifacts are done. It treats an asset older than 24 h with no artifact as "not coming".
- A `visual_descriptions_queried` analytics event fires on each read.

**Flags (observed-network).**
- `visual-descriptions-frame-extractor = temporal-worker`: frames are pulled by a server workflow.
- `visual-search-ui = true`, with `visual_embeddings` as a separate artifact.

**What we keep from that (design):**
- a per-asset artifact made at import
- event-typed entries
- an explicit, range-scoped agent read with a token guard
- a separate embedding index for search

**What we do better (design):**
- **Shot-aware structure.** Shots, then events inside shots, rather than a flat list.
- **Richer fields.** On-screen text, camera motion and quality flags, all of which editing needs.
- **Speech/visual relevance.** We detect off-topic talk.
- **One merged timeline.** Highlight scoring and the agent read speech and visuals together.
- **Visible status and cost.**

## UX (design)

- **Import.** The visual track is on by default for video under 2 h. The media chip shows "Describing visuals… 40%". Longer media or a low credit balance needs an opt-in, and the user sees the estimated cost first.
- **Script view.**
  - A thin **Visuals lane** sits beside the script paragraphs. Each shot shows a one-line caption, for example "Close-up: socket wrench on lug nut".
  - Hovering a caption shows the keyframe thumbnail and its events.
  - Where the talk is off-topic, the lane shows a muted "talk ≠ picture" badge.
- **Wordless spans.** A span with no words (music, B-roll) shows the shot captions inline in the script, in italics, as `[visual] …`. This answers Hunter's B6 confusion directly: the description appears where he expected it. It is a read-only annotation, never script text that could be deleted as words.
- **Search.** A single search box with three scopes: Words / Visuals / Both.
  - Visual hits show thumbnails with a time.
  - Enter jumps the playhead.
  - "Use as B-roll" drops the shot range on a new track.
- **Correct it.** The user can edit a caption or mark it "wrong". An edit is stored as an override and wins on re-runs; it also becomes an eval label.
- **Export.** Off by default. The options are a sidecar `.visual.json` / `.vtt` of descriptions, or chapters built from shot groups. This answers Hunter's B7.

## Inputs / outputs

```text
input:  media asset (video or image), transcript (optional), options
          density: "sparse" | "standard" | "dense"   (default standard)
          budget_cents: number | null
          language: string (default = transcript language or "en")
output: VisualTrack artifact (JSON) + embedding index rows
```

## Algorithm (design)

1. **Shot detection.**
   - TransNetV2 runs at 25 fps on a 48×27 downscale. PySceneDetect `AdaptiveDetector` is the CPU fallback.
   - Merge shots shorter than 0.4 s into their neighbour, unless the cut is hard.
   - Split shots longer than 20 s into **sub-shots** wherever the motion or embedding change peaks.
   - For a still image, the image is one shot.
2. **Adaptive frame sampling.**
   - **Per shot:** 1 frame plus 1 per 4 s, capped at 6.
   - **Extra frames:** at motion peaks (optical-flow magnitude or frame-difference energy) and at OCR-likely frames (an edge-density spike).
   - **Dedupe:** drop near-duplicate frames, where the SigLIP cosine is above 0.95.
   - `density` scales the per-second rate by ×0.5 or ×2.
3. **Cheap signals,** computed locally with no LLM:
   - **Camera motion class:** static / pan / tilt / zoom / handheld / tracking, from global-motion estimation by homography over sparse flow.
   - **Quality flags:** blur (variance of Laplacian), over/under exposure (histogram clipping), shaky (motion jitter), black/frozen frames.
   - **Faces:** count and size; reuses the face track from reframe.
   - **OCR:** on candidate frames.
   - **Embeddings:** one SigLIP 2 image embedding per sampled frame, mean-pooled per shot.
4. **VLM description, per shot.**
   - Send the shot's frames (low or medium resolution) and the shot's transcript slice as context.
   - Ask for structured JSON (schema below): a one-line caption, events with relative times, entities, setting, actions, on-screen text, and a salience 0..1.
   - Batch about 8 shots per call so the model sees continuity. Pass the previous caption to stabilise naming ("the mechanic", not "a man" then "a person").
5. **Speech/visual relevance.** For each shot, `relevance = cos(embed_text(transcript slice), embed_text(shot caption + events))`, using one text-embedding model for both sides.
   - Below 0.25 and the shot has speech → `talk_offtopic = true`.
   - No words → `wordless = true`.
   - Smooth over three shots, so one shot never flips the flag alone.
6. **Index.**
   - Write the `VisualTrack` JSON.
   - Upsert one vector row per shot and one per event, for text search (caption embeddings) and image search (SigLIP).
   - Add BM25 over captions, OCR text and entities for exact terms like part numbers.
7. **Cache.**
   - Key: `(media_sha256, model_id, prompt_version, density)`.
   - Re-runs on a duplicate file or a re-import are free.
   - A user override is keyed by shot id plus a hash of the shot's frame range, so it survives a re-run that produces the same shots.

**Cost control (design).**
- Estimate before running: `n_frames × tokens_per_frame + per-call overhead`. The public reference is Gemini, which samples video at 1 fps by default and costs about 100 tokens per second of video at low media resolution ([Google AI docs, video understanding](https://ai.google.dev/gemini-api/docs/video-understanding), public-research, checked 2026-10-22).
- Our shot-based sampling averages **0.3–0.5 frames/s** on talking-head footage and about 1 frame/s on B-roll, so the cost is well under the 1 fps default.
- Run order: wordless and off-topic spans first, which is where the value is, then everything else.
- Stop at `budget_cents` and mark the rest `pending`. The agent can ask for a range on demand.

## Models / APIs (options)

| Step | Default | Alternatives |
| --- | --- | --- |
| Shot boundaries | TransNetV2 ([arXiv 2008.04838](https://arxiv.org/abs/2008.04838)) | PySceneDetect ([scenedetect.com](https://www.scenedetect.com/)) content/adaptive detectors |
| Frame embeddings | SigLIP 2 ([arXiv 2502.14786](https://arxiv.org/abs/2502.14786)) | OpenCLIP ViT-L/14 |
| VLM captions | Gemini Flash-class with structured output ([docs](https://ai.google.dev/gemini-api/docs/video-understanding)) | GPT-4.1-class vision; open Qwen2.5-VL ([arXiv 2502.13923](https://arxiv.org/abs/2502.13923)) for self-hosting |
| OCR | PaddleOCR | VLM-only (cheaper, worse on small text) |
| Text embeddings | any 768–1024-d text model | Use the same model for transcript and captions |
| Vector store | pgvector (we already run Neon/Postgres) | LanceDB, local SQLite-vss for desktop |

## Data model

```text
VisualTrack
  media_id, version, model_id, prompt_version, density, created_at
  status            "pending" | "partial" | "done" | "failed"
  coverage          [{start_s, end_s}]          # ranges described so far
  shots: Shot[]

Shot
  id                string    # stable: hash(media_id, start_frame, end_frame)
  start_s, end_s
  keyframe_s        number
  caption           string    # ≤ 90 chars, present tense, concrete
  events: [{ t_start_s, t_end_s, kind, text }]
       kind ∈ entity | setting | action | foreground_event | background_event | text_on_screen
  entities          string[]  # "mechanic", "torque wrench", "red F-150"
  setting           string    # "home garage, daylight"
  on_screen_text    [{ text, t_s, bbox? }]
  camera            static | pan | tilt | zoom | handheld | tracking
  shot_size         wide | medium | close | extreme_close | screen | graphic
  quality           { blur, exposure, shaky, frozen }    # 0..1 each
  faces             { count, max_area }
  salience          0..1      # "worth showing" per the VLM
  speech            { wordless: bool, relevance: 0..1, talk_offtopic: bool }
  override?         { caption?, events?, wrong?: bool, by, at }
```

## Agent exposure (design)

- `query_visuals {media_id | composition_id, range?, query?, kinds?, max_tokens=1500}`. It returns compact lines:
  ```text
  [12.4–18.0] close · handheld · "Hands loosen lug nuts with breaker bar" · text:"20 mm" · talk≠picture
  ```
  With a `query`, it returns the top-k hits from the search index (hybrid vector + BM25) instead of a range dump. Over budget, it returns the Descript-style `oversized` hint with a suggested narrower range.
- `query_script_markdown` gains `include_visuals: "none" | "wordless_only" | "all"`, default `wordless_only`. Wordless spans and off-topic stretches are then never invisible to the model, and the cost stays small.
- `wait_for_visual_descriptions {media_ids, timeout_s}` returns partial coverage instead of blocking.
- The agent prefers `query_visuals` over `screenshot`. A screenshot is for checking a frame it has just *changed*, such as framing (prompt catalog B4 shows screenshot loops do not converge).

## Edge cases

| Case | Behaviour |
| --- | --- |
| Screen recording | Shot detector sees few cuts. Use OCR-heavy sampling and caption the UI state ("Settings › Billing open"). `shot_size = screen` |
| Static talking head for 40 min | One shot split into sub-shots every 20 s. Captions note gesture or prop changes only. Cost stays low |
| Rapid cuts (music video) | Merge sub-0.4 s shots for captioning, but keep boundaries for montage beat-sync |
| Privacy | Captions describe people by role or appearance, never by identity guesses. Faces are not recognized |
| Unsafe content | The VLM reports a `content_flag` and the description is still stored. Search hides it unless opted in |
| VLM hallucination | `salience` and events are capped by local signals. For example, "zoom" claims must agree with the camera class. Low-agreement shots are marked `low_confidence` |
| Re-transcribe / re-import | The visual track is keyed by media hash, so it does not re-run |
| Language | Captions in the project language. Entities kept in the source language when they are on-screen text |

## Eval / metrics

- **Retrieval.** Recall@5 for a labelled query set of 200 queries over 20 owned videos (shop, cooking, screen, talking head), plus MRR.
- **Caption quality.** Human 1–5 for accuracy and specificity on 300 shots. Target ≥ 4.0. Hallucinated entity rate < 3%.
- **Off-topic detection.** F1 against human labels "talk matches picture?". Target ≥ 0.8.
- **Downstream.** Agent task success on 30 visual-edit prompts ("put the welding close-ups over the intro"), with and without the visual track. Also the share of screenshot calls per turn (should drop).
- **Cost.** Cents per media hour, p50 and p95. Seconds of latency per media minute.

## MVP vs later

- **MVP:**
  - PySceneDetect shots
  - fixed sampling (1 + 1 per 5 s)
  - one VLM call per 8 shots with the JSON schema
  - caption + events + on_screen_text + camera
  - caption-embedding search
  - `query_visuals`
  - the `include_visuals: wordless_only` flag
  - the Visuals lane
- **Later:**
  - TransNetV2
  - motion-peak sampling
  - SigLIP image search ("find frames like this one")
  - OCR model
  - override-driven fine-tuning
  - export sidecar
  - per-speaker on-screen detection
  - multi-asset "find every shot of the red truck"
