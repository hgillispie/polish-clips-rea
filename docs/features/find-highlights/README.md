# Find Highlights + Make Clips / Shorts / Reels

Turn a long recording into ranked, self-contained vertical clips. Each clip ships **ready to post**:
- reframed 9:16
- captioned
- optional B-roll
- **a title, a hook (on-screen text for the first 1–3 s plus a spoken/caption hook) and a platform-ready description with hashtags**, per target platform

This closes the HANDOFF backlog item **"find-highlights scoring"**. The product shape is aligned with OpusClip, which is the market reference for this feature. Descript's version is thin; see the evidence below.

Depends on:
- [visual descriptions](../visual-descriptions/README.md): visual signals and grounding
- [platform profiles](../publish-metadata/platform-profiles.md): durations, limits, safe zones, hashtags
- [publish metadata](../publish-metadata/README.md): the validation and repair used for packaging

Pseudocode: [../../pseudocode/find-highlights.md](../../pseudocode/find-highlights.md).

## Evidence

**What Descript did in the capture (observed-network).** Hunter asked to "make 3 short clips for tiktok" (B3 in [prompt-catalog](../../descript-analysis/underlord/prompt-catalog.md)). The agent:
- loaded the `create-clips` skill
- read the script once at 3-s timestamp granularity
- called `copy_script_segments` three times with chosen time ranges
- set portrait layout and captions
- then looped on screenshot → modify to fix framing

No highlight endpoint fired, so clip choice was the chat model reading the transcript ([observed-network §Find highlights](../../descript-analysis/underlord/observed-network.md#find-highlights--make-clips-observed-network-backlog-input)). The clips were about 15–25 s, with no score and no title/hook/description per clip.

**Descript client (decompiled).**
- AI-tool presets `find-highlights`, `make-clips` and `make-highlight-reel`; the last takes `targetDuration` and a layout `templateDetails` ([prompt-actions](../../descript-analysis/ai-tools/prompt-actions.md#non-text-actions-in-the-same-panel)).
- A legacy clips action endpoint on the project.
- A `take_clip` agent tool (preview-resolution render, flag off).

**What we take from Descript:**
- the agent workflow shape ([create-clips-workflow](../../pseudocode/underlord/create-clips-workflow.md))
- clips as new compositions that reference source ranges, so they are non-destructive

**What we replace:** "the LLM eyeballs the whole transcript" becomes a scored, multimodal pipeline.

**OpusClip (public-research and static-help).**
- A **virality score 0–99** with sub-scores **Hook, Flow, Value, Trend** (Engagement added in ClipAnything 3.0).
- Results sort by score or chronologically.
- Clip length "Auto (0–3 min)" or fixed buckets; topic keywords; a timeframe range.
- Auto hook, ReframeAnything subject tracking, AI B-roll, captions with emoji and keyword highlight, and auto title/description/hashtags.
- The public API clip object has `timeRanges[]` (**a clip can be several ranges**), `title`, `description`, `hashtags`, `genre`, and `durationMs`.

Sources: [help.opus.pro](https://help.opus.pro/), [API docs](https://help.opus.pro/api-reference/overview), and the [virality score explainer](https://help.opus.pro/docs/article/virality-score). We record the shape, not their code. The scoring internals are not public.

**Academic (public-research).**
- **Highlight detection and moment retrieval:**
  - QVHighlights / Moment-DETR ([arXiv 2107.09609](https://arxiv.org/abs/2107.09609)) gives saliency per 2-s clip.
  - UMT ([2203.12745](https://arxiv.org/abs/2203.12745)) is audio+visual.
  - UniVTG ([2307.16715](https://arxiv.org/abs/2307.16715)).
  - "Less is More" learns highlights from user-edited video length ([1903.00859](https://arxiv.org/abs/1903.00859)).
- **Video summarization benchmarks:** TVSum, SumMe.
- **Active speaker:** TalkNet ([2107.06592](https://arxiv.org/abs/2107.06592)), Light-ASD (CVPR 2023).
- **Laughter detection:** Gillick et al., Interspeech 2021 ([ISCA](https://www.isca-archive.org/interspeech_2021/gillick21_interspeech.html)).

We use these as **signals and eval methodology**. The primary ranker is an LLM rubric fused with cheap signals, because talk content is what makes a short work.

## User stories

- **Podcast.** I upload a 70-min podcast, choose TikTok + Shorts, and click **Find clips**. In about 3 min I get 12 clips sorted by score (0–99). Each has sub-scores, a reason ("strong contrarian opener; payoff at 0:38"), and a ready title, hook and caption per platform.
- **Steering.** I type "only about pricing, 30–45 s" and get only those.
- **Editing a pick.** I drag a clip's start earlier by one sentence, and its packaging regenerates for the new range.
- **Multiple ranges.** One clip skips a 20-s tangent in the middle (two ranges, invisible jump-cut covered by a punch-in).
- **Export.** I export 5 clips in one go, as MP4s plus a JSON/CSV of title/hook/description/hashtags per platform.
- **Agent.** The agent ("make 3 clips about the welding part") calls `find_highlights` instead of reading the whole script, so it is cheaper and better.

## UX (design)

**1. Setup sheet.**
- **Platform chips:** TikTok, Shorts, Reels, Facebook. Pick several. This sets the duration targets and packaging.
- **Length:** Auto, or a range slider (default from the profile `sweet_spot_s`).
- **Count:** Auto or N.
- **Topic/keywords:** free text.
- **Timeframe:** an optional range of the source.
- **Layout:** Auto, Fill, Split, Fit, Screen+cam.
- **Toggles:** Captions (style picker from [caption-style](../../pseudocode/caption-style.md)), Hook text, B-roll, Cold-open hook.

The setup sheet shows a cost/time estimate.

**2. Results grid.** Cards are sorted by **Score**. They can also sort by **Timeline** order, and filter by duration, platform fit and topic. Each card has:
- a 9:16 preview (hover plays)
- a score badge, e.g. `87`
- four sub-score bars: Hook / Flow / Value / Trend
- duration, a source timecode link, and a one-line "why"
- a **platform tab strip** showing that platform's **Title**, **Hook** (on-screen text plus spoken/caption hook) and **Description + hashtags**, each with a counter vs. the profile limit (e.g. `43/100`, `#4/5`)

**3. Clip detail.** Opens on a card. Contains:
- the transcript of the range, with draggable sentence-snapped handles; "extend to previous/next sentence" buttons
- multi-range editing (strike a sentence to drop it)
- a hook editor: text, the 1–3 s window, position in the safe zone, style
- a reframe preview with the speaker track and a manual keyframe override
- B-roll suggestions inline (visual-track matches first, then stock)
- packaging fields with regenerate / lock / quick rewrites, the same component as [publish metadata](../publish-metadata/README.md#ux-design)

**4. Actions.**
- **Keep** creates a composition; **Discard**.
- **More like this** re-runs with this clip's topic as seed.
- **Export selected** produces MP4s plus a packaging sidecar.

Feedback is logged: keep/discard, edits to boundaries and text.

**5. Agent.** The tool `find_highlights` returns compact candidates. The `create-clips` skill uses them and asks for plan approval with the list (titles + scores) before it builds compositions.

## Inputs / outputs

```text
input:
  source: composition_id | media_id
  platforms: PlatformKey[]                 # ≥1; drives duration + packaging
  length: "auto" | {min_s, max_s}
  count: "auto" | int
  topic?: string; timeframe?: {start_s, end_s}
  layout: "auto"|"fill"|"split"|"fit"|"screen_cam"
  options: {captions: bool, hook_text: bool, cold_open: bool, broll: bool, language?}
  brand?: Brand                            # shared with publish metadata
output:
  HighlightResult { clips: Clip[] (sorted by score), stats, cost }
```

## Algorithm (design)

**Stage 0. Prerequisites (cached analysis artifacts).**
- Transcript with word times and speakers.
- [Visual track](../visual-descriptions/README.md).
- Audio features at a 100 ms hop: loudness (LUFS-S), pitch variance, speech rate.
- Laughter/applause probability (PANNs AudioSet tags `Laughter`, `Applause`, `Cheering`, [1912.10211](https://arxiv.org/abs/1912.10211)).
- Face tracks + active speaker (TalkNet/Light-ASD) for reframing.
- Motion energy.

**Stage 1. Units and topics.**
- Split into **sentences** (punctuated transcript; for very long run-ons, split at silence ≥ 300 ms).
- Group sentences into **topic segments**: TextTiling-style boundaries on sentence-embedding similarity, with a depth score over 1 σ.
- Each sentence gets:
  - an `opener` probability (cheap classifier or heuristics: questions, bold claims, "the biggest mistake…", numbers, contrast words; no dangling anaphora such as "so that's why", "and he")
  - a `closer` probability (a conclusion or punchline, falling pitch, followed by a pause ≥ 400 ms, or laughter)

**Stage 2. Candidate windows.**
- For each sentence `i` with opener ≥ 0.3, and each `j ≥ i` in the same or the next topic segment with `dur(i..j)` inside `[min_s, max_s]` of the strictest selected platform (see "Duration targets"), the window is a candidate when sentence `j` is closer-capable.
- **Prefilter** to the top K (K = 8 per 10 min of source, minimum 30) by a cheap score: 0.3 opener + 0.2 closer + 0.2 energy z + 0.1 laughter + 0.1 topic match + 0.1 visual salience.
- Run NMS at IoU 0.6 so the LLM sees variety.

**Stage 3. LLM rubric + packaging (one call per batch of about 6 candidates).** The input per candidate:
- the transcript text with speaker labels
- the visual track lines for the range (`query_visuals`, compact)
- 1 sentence of context before and after
- the topic, the selected profiles, and brand rules

The output is strict JSON:
- **Scores** 0–10:
  - `hook`: do the first 3 s stop the scroll?
  - `flow`: coherent, no dead air, no unresolved references
  - `value`: insight, emotion, humour or utility
  - `trend`: topical and shareable; optional, uses a trends list when configured, otherwise "broad appeal"
  - `standalone`: understandable with zero context
  - `payoff_present`: bool
- **Trims:** `trim_start_sentences`, `trim_end_sentences` to tighten, and `drop_sentences[]` for multi-range.
- **`cold_open_candidate`:** the best 2–4 s line inside the clip to tease up front, or null.
- **`packaging` per platform:** `title`, `hook{on_screen_text, spoken, caption_hook}`, `description`, `hashtags[]`, `rationale`.

Doing packaging in the same call is deliberate. The model has just reasoned about why the clip works, so the title and hook come from the same understanding. Validation is a separate deterministic step afterwards.

**Stage 4. Fusion score (0–99).**

```
llm  = 0.30·hook + 0.25·value + 0.20·flow + 0.15·standalone + 0.10·trend      (0–10)
sig  = 0.35·energy_z⁺ + 0.25·laughter + 0.15·face_engagement + 0.15·visual_salience + 0.10·speech_rate_fit
pen  = 2·offtopic_ratio + 3·[!payoff_present] + 1.5·dead_air_ratio + 2·[starts_mid_thought]
raw  = 0.75·llm + 2.5·sig − pen
score = round(99 · sigmoid((raw − 5.5) / 1.3))
```

- The MVP uses these hand weights. Later, fit a pairwise learning-to-rank model on keep/discard feedback, as Less-is-More does with user edits.
- The four UI sub-scores are hook, flow, value and trend, each × 9.9 and rounded, for familiarity with OpusClip.

**Stage 5. Dedupe and selection.**
- Sort by score. Greedily accept a clip when:
  - temporal IoU with every accepted clip is ≤ 0.3 (overlap rule)
  - **and** transcript-embedding cosine is ≤ 0.85 (semantic dedupe: no two clips making the same point)
- Then stop at `count`, or "auto" (score ≥ 60, max 1 per 3 min of source, cap 30).
- Keep diversity across topic segments: at most 3 per segment unless `count` demands more.

**Stage 6. Boundary snapping.**
- **Start:** snap to the sentence's first word onset minus 80 ms. Leading fillers ("um", "so,", "yeah") are removed via the filler model. The start must not be within 150 ms of the previous word's end; if it is, cut on the word boundary with a 30 ms fade.
- **End:** the last word's end plus a 250–600 ms tail, ending in silence or at the end of laughter. Never cut inside laughter or applause; extend up to 2 s, else end before it starts.
- **Multi-range:** dropped sentences become gaps. Each join is word-boundary cut + 2-frame audio crossfade, and the video gets a punch-in (scale 1.08–1.15) or a cutaway (B-roll) to hide the jump. At most 3 ranges, and a dropped gap must be ≥ 3 s, otherwise keep it.
- **Duration targets:** after snapping, `duration ∈ [min_s, max_s]` of each selected profile. When the platforms conflict (e.g. a 70-s clip is fine for Shorts but outside the TikTok sweet spot), mark per-platform fit rather than dropping. A 45-s clip fits all.

**Stage 7. Cold-open hook (optional).**
- When `cold_open` is on and the LLM gave `cold_open_candidate` with high hook value, prepend that 2–4 s line, then a 6-frame whip or flash transition, then the clip from its start.
- The line also stays in its original place. Mark this in the UI ("teaser").
- Off by default for interviews where it may misrepresent context.

**Stage 8. Reframe to 9:16.**
- Active-speaker track: per-frame ASD scores, then the speaker box, then a smoothed crop path. This follows [center-active-speaker](../../pseudocode/center-active-speaker.md): one-euro / critically damped spring, dead-zone 6% of width, max pan 0.6 width/s, a hard cut on speaker change if the face is more than 25% away.
- **Layouts:**
  - *Fill*: a single crop.
  - *Split*: two speakers stacked when both are active within 4 s of each other.
  - *Fit*: blurred background, for wide shots and screen content.
  - *Screen+cam*: screen on top 60%, face below, when the visual track says `screen_recording` and a face track exists.
- **Auto** picks per shot from the visual track (shot size, faces count, screen recording).

**Stage 9. Captions and hook text.**
- Captions come from [captions](../../pseudocode/captions.md) + [caption-style](../../pseudocode/caption-style.md): word-highlight style, 1–3 words per cue for TikTok/Reels, keywords emphasized (nouns/numbers from the fact sheet).
- Position at y = 55–62%, inside the union safe zone.
- **Hook text** (`hook.on_screen_text`) shows from 0.0 s to `min(3.0, first sentence end)` in the top band (y 18–30%), with high contrast, ≤ 8 words.
- Never cover the speaker's face: check overlap with the face box and move it if needed.

**Stage 10. B-roll hooks (optional).** Insertion points, at most 1 per 8 s:
- static talking-head stretches over 8 s
- multi-range joins
- concrete nouns spoken (e.g. "ceramic coating", "lug nut")

Source order:
1. the same project's visual track (`query_visuals(query=noun)`, footage the user owns)
2. stock ([stock-asset-providers](../../pseudocode/editor/stock-asset-providers.md))
3. generated images or video (opt-in)

B-roll covers the top 60%, or goes full-frame with captions on top, for 1.5–3 s.

**Stage 11. Packaging validation.**
- For each clip and platform, run [publish-metadata `validate_and_repair`](../../pseudocode/publish-metadata.md#validation-deterministic-first) against the profile: limits, hashtag cap, banned words, grounding against the clip's transcript + visual lines, and the clickbait check.
- Re-generate only the failing fields.
- When the user edits clip boundaries, invalidate and regenerate that clip's packaging.

### Packaging: title, hook, description

Every clip, for every selected platform, carries:

| Field | Rule | Profile-driven |
| --- | --- | --- |
| `title` | ≤ profile `title.max_chars`, front-loads the payoff or keyword; for TikTok/Reels/Facebook, which have no title field, it becomes the **cover text** and the composition name | YouTube Shorts: ≤ 100 (≤ 40 visible) |
| `hook.on_screen_text` | ≤ `hook.on_screen_text_max_words` (7–9), shown 0–`hook.window_s[1]` s; a curiosity gap or bold claim **that the clip pays off** | window: TikTok 1.5 s, Reels/Shorts 2 s, Facebook 3 s |
| `hook.spoken` | A suggested opening line the creator could re-record or use as AI voice (opt-in), ≤ 12 words; or "use original" when the first sentence already hooks | — |
| `hook.caption_hook` | The first line of the caption (what shows before "more"), ≤ profile `caption.show_chars` | 90–125 chars visible |
| `description` | caption_hook + 1–2 lines of value/context + optional CTA question; brand suffix; ≤ `caption.max_chars` (UTF-16 for the TikTok API) | per profile |
| `hashtags` | 0–N specific tags, `#CamelCase`, at most the profile `hashtags.max` (YouTube 3 shown, TikTok 3–5, Reels ≤ 5, Facebook 0–3); appended per `placement` | per profile |

Grounding: every claim in title, hook or description must come from the clip's own transcript or visual lines, not from elsewhere in the source. The clickbait check applies to the title and the hook.

## Models / APIs (options)

| Need | MVP | Options |
| --- | --- | --- |
| Rubric + packaging LLM | Gemini 2.5 Flash-class (cheap, long context, JSON) | GPT-4.1-mini-class, Claude Sonnet-class for the top-N re-score |
| Sentence/topic embeddings | bge-m3 or text-embedding-3-small-class | — |
| Laughter/applause | PANNs CNN14 (AudioSet) | Gillick laughter model |
| Active speaker | Light-ASD | TalkNet; face detector SCRFD/RetinaFace + tracker ByteTrack |
| Visual | [visual track](../visual-descriptions/README.md) | Direct VLM on frames for the top-N only (re-check hook frames) |
| Captions | our caption pipeline | — |
| B-roll | visual track + stock | generated image/video (Gemini image, Veo/Kling-class) |

Cost control: the prefilter means the LLM sees about 8 candidates per 10 min, in batches of 6, which is about 1 call per 7 min of source.

## Data model

```text
HighlightJob { id, source_ref, params, status: queued|running|done|failed|canceled, progress, cost_cents, created_at }
Clip
  id, job_id, rank
  ranges: [{media_id, start_s, end_s}]            # ≥1; source time; multi-range allowed
  duration_s
  score: 0..99
  subscores: {hook, flow, value, trend: 0..99, standalone: 0..99}
  signals: {energy_z, laughter, face_engagement, visual_salience, offtopic_ratio, dead_air_ratio}
  reason: string                                  # one line, shown on the card
  topic_segment_id, keywords[]
  platform_fit: {platform: "fits"|"long"|"short"}
  cold_open?: {media_id, start_s, end_s}
  layout: {mode, per_shot_overrides[], crop_path_ref}
  captions: {style_id, enabled}
  hook_overlay: {text, start_s: 0, end_s, box, style_id}
  broll: [{at_s, dur_s, asset_ref, source: "project"|"stock"|"generated"}]
  packaging: { [platform]: ClipPackaging }
  status: candidate|kept|discarded|exported
  composition_id?                                 # set on Keep
ClipPackaging
  platform, profile_version
  title: string
  hook: {on_screen_text: string, spoken: string, caption_hook: string}
  description: string
  hashtags: string[]
  checks: Check[]; locks: {field: bool}; grounding: [{field, span_ref, sim}]
Feedback { clip_id, action: keep|discard|edit_bounds|edit_text|export, delta?, at }
```

## Edge cases

| Case | Handling |
| --- | --- |
| Source < 2 min | Return 1–3 clips. Allow a whole-source clip |
| No speech (music, sports, vlog B-roll) | Visual-only mode: candidates from shot salience + audio energy peaks; packaging from visual lines; mark "low grounding" |
| Screen recording / tutorial | Layout screen+cam or fit. Hook favours the result shown ("before/after") |
| Many speakers / crosstalk | Split layout. Captions with speaker colour. Penalize flow when overlap is > 20% |
| Profanity or sensitive content in the hook | Respect `brand.profanity` (allow / bleep / avoid). Never put slurs in on-screen text |
| Claims about real people | Grounding is mandatory. No defamation-prone rewording ("allegedly" stays) |
| Context-dependent joke (needs setup) | `standalone` low, so the model should propose a multi-range that includes the setup |
| The user edited the composition already | Candidates map through the composition to source ranges. Cut words are excluded |
| Language not English | Rubric and packaging in the source language. Hashtags in that language, unless the brand overrides |
| Very long source (4 h stream) | Per-hour candidate quota, so it is not dominated by one segment. Streaming results |
| User re-runs with a topic | Reuse stages 0–1, rerun from stage 2 |

## Eval / metrics

**Offline set.** 40 long videos (podcasts, tutorials, vlogs, streams), each with **creator-chosen clips** as positives: clips they actually posted, plus 3 raters marking all "would post" spans.

**Ranking.**
- Precision@5 / NDCG@10 against human picks (a candidate counts as a hit if IoU ≥ 0.5 with a positive).
- Reference: QVHighlights-style HIT@1 for saliency.

**Clip quality (human audit of 100 clips).**
- Standalone rate ≥ 85%.
- Starts mid-thought ≤ 3%.
- Ends before payoff ≤ 5%.
- Bad reframe (face cut) ≤ 2% of frames.

**Packaging.**
- Limit violations = 0.
- Ungrounded claims < 2%.
- Hook judged "would stop scroll" ≥ 60% vs a baseline of the first sentence.
- Pairwise preference vs. OpusClip outputs on the same sources (blind) ≥ 50% win/tie.

**Online.**
- Keep rate, edit-distance on boundaries, and export rate.
- With opted-in analytics: 3-s hold, completion, shares.

**Score calibration.** Clips scoring 80+ should be kept ≥ 2× as often as clips scoring 60–70.

## MVP vs later

- **MVP:**
  - transcript-driven candidates
  - the LLM rubric + packaging call
  - energy + laughter + off-topic signals
  - NMS + semantic dedupe
  - sentence/silence snapping
  - single-range clips
  - Fill/Fit reframe with active speaker
  - captions
  - hook text overlay
  - packaging for 4 short-form platforms, validated
  - grid UI with edit handles
  - JSON/CSV packaging export
  - the `find_highlights` agent tool
- **Later:**
  - multi-range clips
  - cold-open hook
  - Split and Screen+cam layouts
  - B-roll insertion
  - learned fusion weights from feedback
  - trend feed
  - spoken-hook re-record / AI voice
  - per-brand few-shot from analytics
  - direct posting
