# Highlight Reel

A single 30–90 s (or longer) montage that sums up a long recording or a set of clips: a trailer for an episode, a recap of an event, a "best of" a stream. It reuses the scored moments from [Find Highlights](../find-highlights/README.md) and adds:
- an **intro hook**
- **ordering**: chronological or narrative arc
- **transitions**
- a **target-duration solver**

Pseudocode: [../../pseudocode/highlight-reel.md](../../pseudocode/highlight-reel.md).

## Evidence

**Descript (decompiled).** The `make-highlight-reel` preset (AI action `create_highlight_reel`) takes `targetDuration` ("Max duration") and `templateDetails` (layout) ([prompt-actions](../../descript-analysis/ai-tools/prompt-actions.md#non-text-actions-in-the-same-panel)). The API docs list "create a 30-second highlight reel" as an example prompt ([api-notes](../../api-notes.md)). It was not run in the capture, so there is no network evidence.

**Prior art (public-research).**
- Video summarization as a knapsack: pick segments that maximize importance under a length budget. This is the standard formulation on TVSum/SumMe; see the KTS + knapsack setup in Zhang et al., "Video Summarization with LSTM" ([arXiv 1605.08110](https://arxiv.org/abs/1605.08110)).
- OpusClip narrative templates ([help.opus.pro](https://help.opus.pro/)).

**Design.** Everything below.

## User stories

- **Trailer.** "60-second trailer for this episode." I get a reel that:
  - opens on the boldest line (hook, about 3 s)
  - runs 5–8 moments in story order (setup → tension → payoff)
  - ends on a CTA card
  - is 60 ± 1 s, with music ducked under the speech
- **Event recap.** "Recap of the conference day, chronological, 90 s." The moments come from 6 different files, in clock order, with crossfades and a lower-third per speaker.
- **Re-ordering.** I drag one moment out and the solver refills to the target. I lock a moment so it is never removed.

## UX (design)

- **Setup.**
  - Target duration: 15 / 30 / 60 / 90 / custom, with tolerance ±1 s by default.
  - Ordering: **Story arc**, **Chronological** or **Best first**.
  - Aspect: 16:9 / 9:16 / 1:1.
  - Style: Clean cut / Crossfade / Energetic (whips on beats).
  - Intro hook on/off; End card (text + CTA); Music (none / library / mine) with auto-duck.
  - Sources: this composition, selected clips, or a whole folder.
- **Result.**
  - A strip of moment tiles on a timeline, colour-coded by arc role (hook, setup, build, payoff, outro).
  - Duration meter, e.g. "59.8 / 60 s".
  - Actions: swap a tile for its alternates (the next best of the same role), lock, shorten/extend (sentence-snapped), regenerate.
- **Packaging.** The reel also gets title/description per platform via [publish metadata](../publish-metadata/README.md).

## Inputs / outputs

```text
input: sources[], target_s, tolerance_s=1.0, ordering, aspect, style, intro_hook: bool, end_card?, music?, platforms[]
output: Reel { moments: Moment[], transitions[], music?, end_card?, duration_s, composition_id, packaging }
```

## Algorithm (design)

1. **Moments.** Run Find Highlights stages 0–4 with **shorter windows** (3–15 s, sentence-bounded; "beats", not full clips). Each moment gets a fused score, a topic segment, a time, a speaker, and an **arc role** label from the LLM (`hook | setup | build | payoff | outro | none`).
   - Inputs that are already clips are split into their best sentences.
   - Multi-source inputs use synced time when available ([auto-audio-sync](../auto-audio-sync/README.md)), else file order.
2. **Intro hook.** Pick the moment with the max `hook` sub-score, 2–5 s long. It must not reveal the payoff, by an LLM check against the payoff moment.
   - Place it first, then a 6-frame flash/whip into the body.
   - It is excluded from the body to avoid repeats, unless the ordering is chronological and its original place matters, in which case it is shown twice and marked "teaser".
3. **Selection (target-duration solver).** A 0/1 knapsack with diversity:
   - **Maximize** `Σ score_i − λ·redundancy + μ·coverage`. Redundancy is pairwise cosine > 0.8; coverage is the topic segments covered.
   - **Subject to:**
     - `Σ dur_i + Σ transition overlap + hook + end_card ∈ [target − tol, target + tol]`
     - for `story_arc`: at least one setup and one payoff
     - per-speaker max share 60%
     - locked moments included
   - **Solver.** An exact DP over durations in 0.1-s units (target ≤ 300 s gives ≤ 3000 buckets) for the base knapsack, then a local-search swap pass for the redundancy and coverage terms. For more than 200 moments, use a greedy ratio pass first, then swaps.
   - **Fine fit.** If the solver lands within ±3 s but outside tolerance, adjust the trim tails (0–400 ms per moment) and the transition lengths. Never cut words.
4. **Ordering.**
   - *Chronological*: by source time.
   - *Best first*: descending score after the hook.
   - *Story arc*: order by role (setup → build → payoff → outro), chronological within a role. Then an LLM coherence pass on the sequence of transcripts may swap adjacent tiles to fix a dangling reference. At most 3 swaps; accept only if a coherence judge improves.
5. **Transitions.** By style:
   - *Clean*: hard cut on the word boundary with a 2-frame audio crossfade.
   - *Crossfade*: 8–12 frames.
   - *Energetic*: whip/zoom on music beats (beat grid from [media montage](../media-montage/README.md#algorithm-design)). The moment edges shift to the nearest beat within ±150 ms by adjusting the silence tails.

   A speaker change between consecutive moments prefers a hard cut. The same speaker on the same shot needs a punch-in to avoid a jump cut.
6. **Music.** Optional. Pick a track whose BPM and energy fit the style, and loop or trim it at bar boundaries to the reel length. Ducking: sidechain on the speech VAD, −12 dB under speech, 300 ms attack/release. The end card lands on the final downbeat.
7. **Assemble.** Build a composition with source ranges, layout ([find-highlights reframe](../find-highlights/README.md#algorithm-design) for 9:16), captions, lower-thirds (speaker names if known), and the end card. One undoable commit.

## Models / APIs

- Same as Find Highlights for scoring.
- An LLM for arc roles and the coherence pass.
- Beat tracking (Beat This! / madmom) for Energetic style.
- No new paid APIs.

## Data model

```text
Reel { id, source_refs[], params, moments: [{id, media_id, start_s, end_s, score, role, locked, alternates: moment_id[]}],
       hook_moment_id, order: moment_id[], transitions: [{after_moment_id, kind, frames}], music?: {asset_id, in_s, gain_db},
       end_card?: {text, cta, dur_s}, duration_s, composition_id, packaging: {platform: ClipPackaging} }
```

## Edge cases

- **Target longer than the available good content.** Lower the score floor. If it is still short, report "max achievable 41 s" and offer that.
- **Target very short (≤ 15 s).** Hook + 2–3 moments, no end card unless asked.
- **Single speaker monologue with a static camera.** Punch-ins alternate 1.0 / 1.12 scale to avoid jump cuts.
- **Music with lyrics under speech.** Prefer instrumental; warn otherwise.
- **Moments across sources with different audio levels.** Loudness-normalize each moment to −16 LUFS (or the platform target) before the mix.

## Eval / metrics

- Duration error = 0 outside tolerance (hard).
- Human ratings (1–5) on "makes me want to watch the full video" and on coherence.
- Redundancy rate (pairs over 0.8 cosine) = 0.
- Pairwise preference vs. a top-k-by-score baseline in time order (target ≥ 65% preferred).
- Online: trailer CTR to the full video (when linked).

## MVP vs later

- **MVP:** moments from Find Highlights; hook; knapsack solver; chronological and best-first ordering; clean and crossfade transitions; end card; captions; packaging.
- **Later:** story-arc ordering with the coherence pass; music + beat-snapped Energetic style; multi-source event recap with speaker lower-thirds; alternates swapping UI; per-brand templates.
