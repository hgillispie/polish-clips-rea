# Publish metadata (pseudocode)

Spec: [../features/publish-metadata/README.md](../features/publish-metadata/README.md). Profiles: [../features/publish-metadata/platform-profiles.md](../features/publish-metadata/platform-profiles.md). Chapter rules: [youtube-titles-descriptions.md](youtube-titles-descriptions.md#chapters). All of this is **design**.

```text
function publish_kit(source, platforms, brand, goal="reach", n_variants=2) -> PublishKit:
  profiles = load_profiles("config/platform_profiles.yaml")        # versioned
  facts = fact_sheet(source)                                        # cached by (source hash, model, prompt_v)
  kw = keywords(source, facts)
  kit = PublishKit()
  for p in platforms:
    prof = profiles[p]
    cands = draft(facts, kw, prof, brand, goal, n=2*n_variants)
    cands = [validate_and_repair(c, prof, brand, facts) for c in cands]
    cands = [c for c in cands if c.ok]
    ranked = judge_tournament(cands, prof, facts)
    kit.per_platform.append(PlatformPackage(platform=p, profile_version=prof.version,
                            variants=diversify(ranked, n_variants, cos_max=0.9)))
  if any(p == "youtube_long" or profiles[p].cover for p in platforms):
    kit.thumbnails = thumb_briefs(source, facts, profiles)
  kit.checks = collect_checks(kit)
  return kit
```

## Fact sheet

```text
function fact_sheet(src):
  text = transcript_with_times(src, ignore_cut=true)
  vis  = visual_lines(src, max_tokens=1500)                # from query_visuals
  chunks = split_tokens(text, 8000, overlap=300)
  partial = parallel_map(chunks, ch -> llm_json("facts.v1", {chunk: ch, visuals: vis_in(ch.range)},
                                                schema=FactSheetPartial, temperature=0.2))
  sheet = llm_json("facts_merge.v1", partial, schema=FactSheet) if len(partial) > 1 else partial[0]
  sheet.claims = [c for c in sheet.claims if supported(c, text, vis)]   # embedding sim >= 0.6 to some span
  return sheet
```

## Drafting

```text
function draft(facts, kw, prof, brand, goal, n):
  req = {
    facts, keywords: kw[:10], platform: prof.key, voice: brand.voice or prof.voice,
    limits: {title: prof.title, caption: prof.caption, hashtags: prof.hashtags, hook: prof.hook},
    optimize_for: prof.optimize_for, goal, banned: brand.banned_words, suffix: brand.required_suffix,
    emoji: brand.emoji, language: brand.language or facts.language, n
  }
  return llm_json("publish_draft.v1", req, schema=[DraftVariant], temperature=0.7)
```

`DraftVariant = {title?, description, hashtags[], hook?{on_screen_text, spoken, caption_hook}, chapters?, rationale}`

## Validation (deterministic first)

```text
function validate_and_repair(c, prof, brand, facts, round=0):
  errs = []
  if prof.title and len_units(c.title, prof.title.unit) > prof.title.max_chars: errs += ["title_too_long"]
  if prof.title and prof.title.required and empty(c.title): errs += ["title_missing"]
  if len_units(c.description, prof.caption.unit) > (prof.caption.max_chars or INF): errs += ["caption_too_long"]
  c.hashtags = normalize_tags(c.hashtags)                     # '#', CamelCase, dedupe, strip punctuation
  if len(c.hashtags) > prof.hashtags.max: c.hashtags = c.hashtags[:prof.hashtags.max]   # silent fix
  if prof.hook and c.hook and words(c.hook.on_screen_text) > prof.hook.on_screen_text_max_words: errs += ["hook_long"]
  for w in brand.banned_words: if contains_word(all_text(c), w): errs += ["banned:" + w]
  if brand.required_suffix and not c.description.endswith(brand.required_suffix): c.description += " " + brand.required_suffix
  if "foreign_watermark" in prof.forbid and mentions_other_platform(all_text(c)): errs += ["mentions_other_platform"]
  ung = ungrounded_sentences(c, facts)                        # sim < 0.6 and no exact entity
  if ung: errs += ["ungrounded:" + i for i in ung]
  if c.title and not promise_paid(c.title, facts) : errs += ["clickbait"]
  if not errs: c.ok = true; return c
  if round >= 2:
    c = truncate_to_limits(c, prof); c.ok = not any(e startswith "ungrounded" or e == "clickbait" for e in errs)
    return c
  fixed = llm_json("publish_repair.v1", {candidate: c, errors: errs, limits: prof}, schema=DraftVariant, temperature=0.2)
  return validate_and_repair(fixed, prof, brand, facts, round+1)

function len_units(s, unit): return unit == "utf16" ? utf16_len(s) : grapheme_len(s)
```

## Ranking

```text
function judge_tournament(cands, prof, facts):
  score = {c: 0}
  for (a, b) in round_robin(cands):
    w = llm_json("publish_judge.v1", {a, b, platform: prof.key, facts, criteria:
          ["specific", "curiosity_without_deception", "keyword_early", "voice", "platform_fit"]},
          schema={winner: "a"|"b"|"tie", reason}, temperature=0)
    # judge both orders to remove position bias
    w2 = same with (b, a)
    score[a] += points(w, "a") + points(w2, "b"); score[b] += ...
  return sort_desc(cands, by=score)
```

## Thumbnail / cover briefs

```text
function thumb_briefs(src, facts, profiles):
  shots = visual_shots(src)
  cand = []
  for s in shots:
    if s.quality.blur > 0.3 or s.quality.frozen: continue
    for f in s.face_frames or [s.keyframe_s]:
      sc = 0.35*face_present(f) + 0.25*expression_intensity(f) + 0.2*(1 - clutter(f)) + 0.2*s.salience
      cand.append((sc, f))
  picks = top_k_spaced(cand, k=3, min_gap_s=10)
  return [ThumbBrief(frame_ms=f.ms, overlay_text=overlay_text(facts, max_words=4),
                     overlay_box=place_in_safe_zone(f, profiles), score=sc) for sc, f in picks]
```

## Results loop (later)

```text
on analytics_result(variant_id, metric, value):
  store(brand_id, variant_id, metric, value)
  if enough_results(brand_id, n>=10): brand.few_shot = top_variants(brand_id, by=metric, k=5)
```
