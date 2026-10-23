# Publish metadata generator

This produces platform-ready **titles, descriptions/captions, hashtags, chapters, hook text and thumbnail/cover briefs** for YouTube (long-form and Shorts), TikTok, Instagram Reels and Facebook Reels. It also produces A/B variants.

Per-platform limits, conventions and sources are in **[platform-profiles.md](platform-profiles.md)** (dated 2026-10-22). Find Highlights uses the same profiles and generator for each clip's packaging.

Related evidence and prior specs:
- [../../descript-analysis/youtube-publish-ai.md](../../descript-analysis/youtube-publish-ai.md): Descript's publish AI actions and credit keys (static-bundle)
- [../../pseudocode/youtube-titles-descriptions.md](../../pseudocode/youtube-titles-descriptions.md): the first, YouTube-only spec, with chapters from markers. This feature generalizes it; that file stays the reference for the chapters rules.
- [../../descript-analysis/underlord/prompt-catalog.md](../../descript-analysis/underlord/prompt-catalog.md): Hunter's publish-related prompts in the capture

## User stories

- I finish a 40-min episode and click **Publish kit**. I get a YouTube long title (3 options), a description with chapters, and a thumbnail brief. I also get one caption each for TikTok, Reels and Facebook for the trailer clip. Every limit is enforced and shown as `87/100`.
- I paste my brand rules ("no emojis, always end with the podcast name, never say 'insane'"). Every output obeys them.
- I pick 2 title variants for YouTube A/B. The kit tells me YouTube Studio judges by watch-time share, and stores which variant won when I report back (or when an analytics integration reports it).
- In the clip grid, each clip already has a title, a hook and a description for the platform I selected (see [find-highlights](../find-highlights/README.md#packaging-title-hook-description)).

## UX (design)

- **The publish panel has tabs per platform:** YouTube · Shorts · TikTok · Reels · Facebook.
  - Each field shows a live counter against the profile limit, and the "visible before *more*" cut (`show_chars`) as a faint line.
  - Hashtags are chips with a counter, e.g. `3/5`. An over-cap warning cites the rule: YouTube ignores *all* tags past 60.
- **Each field has** ↻ regenerate, ✎ edit, a "shorter / punchier / more searchable / more formal" quick-rewrite, and a **lock** (locked fields survive a regenerate).
- **Variants.** "A / B / C" pills beside title and thumbnail. "Why this?" opens a one-line rationale, e.g. "names the payoff; keyword 'ceramic coating' is in the first 40 chars."
- **Thumbnail brief.** Three candidate frames picked from the visual track (face + emotion + clean background), each with suggested ≤ 4-word overlay text. "Generate thumbnail" goes to the image model (optional; see Models).
- **Checks strip.** Limit violations, a banned-word hit, missing chapters, "title promises something not said in the first 60 s" (clickbait check), and a foreign watermark detected (Reels).
- **Export.** Copy-all per platform, a `.json` sidecar, or a direct-post API where the integration exists (later). Nothing posts without explicit confirmation.

## Inputs / outputs

```text
input:
  source: { composition_id | clip_id }
  transcript (words + speakers), visual track (../visual-descriptions), chapters/markers
  platforms: PlatformKey[]
  brand: { voice?, banned_words[], required_suffix?, emoji: "none"|"some"|"lots", hashtag_pool?: string[], language }
  goal?: "reach" | "search" | "community"        # default reach
  n_variants: 1..3
output:
  PublishKit { per_platform: PlatformPackage[], thumbnails: ThumbBrief[], checks: Check[], model_meta }
```

## Algorithm (design)

1. **Facts pass.** This is the grounding step and runs once per source.
   - Build a compact **fact sheet**: topic, 5–12 key claims with timestamps, named entities (only those spoken or shown on-screen; no identity guesses from faces), the payoff moment, the audience-level vocabulary, search keywords, a quotable line, and the emotional tone.
   - Inputs: the transcript, the visual track captions and on-screen text, chapters, and the highlight scores when present.
   - Long sources go map-reduce: chunks of about 8k tokens → partial sheets → a merged sheet.
2. **Keyword pass.**
   - Extract candidate search phrases with noun-phrase chunks plus TF-IDF against a generic corpus.
   - Optional: a search-suggest provider, flagged later, never required.
   - Keep phrases that are actually said or shown.
3. **Draft pass, per platform.** An LLM call with *our* prompt, versioned in the repo. Its inputs:
   - the fact sheet
   - the profile (limits, `show_chars`, voice, `optimize_for`, hashtag policy)
   - brand rules
   - the goal
   - `n_variants × 2` candidates

   Platform rules baked into the prompt:
   - **YouTube long:** keyword in the first 40–60 chars; specific over vague; no ALL CAPS. The description's first 150 chars stand alone. Then chapters (from markers or auto-chapters), links block, ≤ 3 hashtags at the end.
   - **Shorts:** a short title (≤ 40 visible). The description is optional, with 1–3 hashtags.
   - **TikTok:** the caption starts with a searchable phrase, then a curiosity line, then 3–5 specific hashtags. No title.
   - **Reels:** the first 125 chars carry the value, with a "send this to…" style prompt only if natural. At most 5 hashtags. Never mention another platform.
   - **Facebook:** plain, complete sentences, a question to invite comments, 0–3 hashtags.
4. **Validate and repair.** These are deterministic checks:
   - Hard limits per the profile, counting in the profile `unit` (TikTok via the API counts UTF-16).
   - Hashtags: cap, dedupe, `#CamelCase`, no spaces, no banned tags; strip tags past the cap.
   - Banned words and the required suffix.
   - **Grounding.** Every claim or number in the copy must map to a fact-sheet item, matched by embedding similarity ≥ 0.6 or exact entity match. Ungrounded sentences get rewritten once, then dropped.
   - **Clickbait check.** The title's promise must be paid off. An NLI/LLM judge asks "is the title's promise delivered in the content?" and wants yes with confidence ≥ 0.7.
   - On a violation: a repair prompt with the specific errors, at most 2 rounds, then truncate at a word boundary.
5. **Rank and choose variants.**
   - An LLM-as-judge pairwise tournament scores the candidates on specificity, curiosity without deception, keyword presence, voice match and platform fit.
   - Return the top `n_variants`, **diversified**: candidate pairs with embedding cosine > 0.9 are deduped.
   - Each variant keeps a 1-line rationale.
6. **Thumbnail / cover brief.**
   - Candidate frames come from the visual track: a face present with a non-neutral expression (local classifier), sharp (blur < 0.3), uncluttered, and salient.
   - Score them and take the top 3 with spacing ≥ 10 s.
   - Overlay text is ≤ 4 words and must not repeat the title verbatim; position it in the profile safe zone.
   - Optional generation: send the frame plus text to the image model. Image-model output must never fabricate a person or a scene that is not in the video (a policy check).
7. **A/B loop (later).**
   - Store `variant_id` on the export. When results come back (manually, YouTube Studio's A/B result, or an analytics API), log `{variant, metric, value}`.
   - Use the winners as few-shot examples for this brand. This learns per channel, not globally.

## Models / APIs (options)

| Step | Default | Options | Notes |
| --- | --- | --- | --- |
| Fact sheet, drafts, repair | mid-tier LLM with JSON mode | Gemini Flash-class, GPT-4o-mini-class, Claude Haiku/Sonnet-class | Temperature 0.7 for drafts, 0.2 for repair |
| Judge | the same model at temperature 0, or a stronger model | — | Pairwise is more stable than absolute scoring |
| Embeddings | text-embedding-3-small-class or bge-m3 | — | grounding and dedupe |
| Thumbnail image | none (frames only) | Gemini image ("nano-banana"), FLUX, Imagen | Edit-from-frame only; no invented people |
| Posting | none in MVP | YouTube Data API `videos.insert` / `thumbnails.set`, TikTok Content Posting API, Instagram Graph API | Needs OAuth and explicit user confirmation each time |

## Data model

```text
PlatformPackage
  platform: "youtube_long"|"youtube_shorts"|"tiktok"|"instagram_reels"|"facebook_reels"
  profile_version: string                 # e.g. "2026-10-22"
  variants: [{
    id, title?: string, description: string, hashtags: string[],
    hook?: { on_screen_text: string, spoken: string, caption_hook: string },
    chapters?: ChapterMarker[],          # youtube_long only
    rationale: string, judge_score: number, grounding: [{sentence_idx, fact_id, sim}]
  }]
  chosen_variant_id
  locks: { field: bool }
ThumbBrief { frame_ms, media_id, overlay_text, overlay_box, score, generated_asset_id? }
Check     { level: "error"|"warn", code, message, field?, platform? }
FactSheet { topic, claims: [{id, text, t_s}], entities[], payoff_t_s, keywords[], quote, tone }
```

## Edge cases

- **Non-English source.** Generate in the source language unless `brand.language` is set. Hashtags in the same language. Grounding works on the translated fact sheet.
- **Very short clip (< 10 s).** No chapters; the description is 1 line.
- **Music-only or silent video.** The fact sheet comes from the visual track and on-screen text only. Mark it "low grounding" in the UI.
- **Sensitive topics** (medical, financial, legal claims). Grounding is mandatory. Never strengthen a hedge ("may help" must not become "cures").
- **Brand rule conflicts with the platform.** For example, a required suffix pushes the copy over the limit. The platform hard limit wins; show a warning.
- **Profile changes.** `profile_version` is stored per package, and old kits are re-validated on open.
- **Hashtag caps that change mid-rollout** (Instagram 30 → 5). Use the strictest documented value.

## Eval / metrics

- **Offline.**
  - Limit-violation rate = 0 (a hard gate).
  - Ungrounded-claim rate < 2%, by human audit of 200 outputs.
  - Clickbait-judge agreement with humans ≥ 0.8.
  - Pairwise human preference vs. our previous version and vs. creator-written copy (target ≥ 50% win/tie).
  - Keyword coverage.
- **Online (opt-in analytics).**
  - YouTube: CTR and average view duration by variant.
  - Shorts, TikTok, Reels: 3-s hold rate, completion rate, shares/sends per reach.
  - Report per brand. Never claim causality from one post.

## MVP vs later

- **MVP:** fact sheet → drafts → validate/repair → judge, for 5 platforms. Profiles from YAML. Counters and locks. Thumbnail frame picks. JSON export.
- **Later:** generated thumbnails, direct posting, the A/B results loop with per-brand few-shot, trend/keyword providers, multilingual variants, per-audience tone presets, a competitor-title similarity check to avoid copying.
