# Find Highlights + Make Clips (pseudocode)

Spec: [../features/find-highlights/README.md](../features/find-highlights/README.md). Uses:
- [visual-descriptions.md](visual-descriptions.md)
- [publish-metadata.md](publish-metadata.md) for validation
- [center-active-speaker.md](center-active-speaker.md) for crop smoothing
- [captions.md](captions.md) for captions

Replaces the `find_highlights` stub in [underlord/create-clips-workflow.md](underlord/create-clips-workflow.md). All of this is **design**.

```text
function find_highlights(src, params) -> HighlightResult:
  job = start_job("find_highlights", src, params)
  A = ensure_artifacts(src, ["transcript", "visual_track", "audio_feats", "laughter", "faces_asd"])
  #   transcript/visual are required; others degrade gracefully (signal = 0, note in stats)
  profs = [profile(p) for p in params.platforms]
  dur = duration_window(profs, params.length)      # {min_s, max_s, target_s}
  sents = sentences(A.transcript, scope=params.timeframe, exclude_cut=true)
  if len(sents) < 5: return visual_only_highlights(src, A, params, profs)
  segs = topic_segments(sents)
  annotate_open_close(sents, A)
  cands = candidate_windows(sents, segs, dur, params.topic, A)
  cands = prefilter(cands, k=max(30, ceil(8 * src.duration_min / 10)))
  scored = []
  for batch in chunk(cands, 6):                      # parallel, rate-limited
    scored += llm_rubric_and_package(batch, A, profs, params, src)
    job.progress(len(scored) / len(cands))
  for c in scored: c.score, c.subscores = fuse(c)
  picked = select(scored, params.count, src.duration_min)
  for c in picked:
    snap_boundaries(c, A, dur)
    if params.options.cold_open: plan_cold_open(c)
    c.layout = plan_reframe(c, A, params.layout)
    c.hook_overlay = plan_hook_overlay(c, A, profs)
    if params.options.broll: c.broll = plan_broll(c, A)
    for p in profs: c.packaging[p.key] = finalize_packaging(c, p, A, params.brand)
  return job.done(HighlightResult(clips=rank(picked), stats, cost=job.cost))
```

## Duration targets

```text
function duration_window(profs, length):
  if length != "auto": return {min_s: length.min_s, max_s: length.max_s, target_s: mid(length)}
  lo = max(p.sweet_spot_s[0] for p in profs); hi = min(p.sweet_spot_s[1] for p in profs)
  if lo > hi: lo, hi = min(p.sweet_spot_s[0]), max(p.sweet_spot_s[1])     # no common range: widen
  hard_max = min(p.duration.max_s or INF for p in profs)
  return {min_s: max(lo * 0.6, 7), max_s: min(hi * 1.5, hard_max), target_s: (lo + hi) / 2}
```

## Units, topics, opener/closer

```text
function topic_segments(sents):
  E = [embed(s.text) for s in sents]
  sim = [cos(mean(E[i-3:i]), mean(E[i:i+3])) for i in 1..n-1]
  depth = [ (max(sim[..i]) - sim[i]) + (max(sim[i..]) - sim[i]) local to ±5 ]
  cuts = [i for i in idx if depth[i] > mean(depth) + std(depth) and gap_since_last_cut >= 60s]
  return segments(sents, cuts)

function annotate_open_close(sents, A):
  for s in sents:
    s.opener = clamp( 0.25*is_question(s) + 0.25*has_bold_claim(s) + 0.15*has_number(s)
                    + 0.15*contrast_word(s) + 0.2*A.audio.energy_z(s.first_2s) > 0
                    - 0.5*dangling_reference(s), 0, 1)
    # dangling_reference: starts with "and", "but so", "that's why", unresolved he/she/it/they/this in first 4 words
    s.closer = clamp( 0.3*pause_after(s) >= 0.4 + 0.25*falling_pitch_end(s) + 0.25*A.laughter.max(s.end, s.end+2)
                    + 0.2*is_conclusion(s), 0, 1)
```

## Candidates and prefilter

```text
function candidate_windows(sents, segs, dur, topic, A):
  out = []
  for i, s in enumerate(sents) if s.opener >= 0.3:
    for j in i..: 
      d = sents[j].end - s.start
      if d > dur.max_s or seg(j) > seg(i) + 1: break
      if d >= dur.min_s and sents[j].closer >= 0.3:
        out.append(Cand(ranges=[(s.start, sents[j].end)], sent_ids=i..j))
  for c in out:
    c.cheap = 0.3*sents[c.i].opener + 0.2*sents[c.j].closer + 0.2*pos(A.audio.energy_z.mean(c))
            + 0.1*A.laughter.mean(c) + 0.1*(topic ? cos(embed(topic), embed(text(c))) : 0.5)
            + 0.1*A.visual.mean_salience(c)
  return out

function prefilter(cands, k):
  return nms(sort_desc(cands, by=cheap), iou=0.6)[:k]
```

## LLM rubric + packaging (one call, batch of ≤ 6)

```text
schema RubricOut = [{
  cand_id,
  scores: {hook, flow, value, trend, standalone: 0..10}, payoff_present: bool,
  trim_start_sentences: int, trim_end_sentences: int, drop_sentences: int[],
  cold_open_candidate: {sentence_id, start_word, end_word} | null,
  reason: string (<= 120 chars),
  packaging: { [platform]: {title, hook: {on_screen_text, spoken, caption_hook}, description, hashtags: string[], rationale} }
}]

function llm_rubric_and_package(batch, A, profs, params, src):
  items = [{cand_id: c.id,
            transcript: speaker_labeled_text(c, A.transcript),
            before: text(sentence_before(c)), after: text(sentence_after(c)),
            visuals: query_visuals(src, range=c.ranges, max_tokens=250).text} for c in batch]
  req = {items, topic: params.topic, language: params.options.language or A.transcript.lang,
         platforms: [profile_brief(p) for p in profs],     # limits, hook window, hashtag max, voice
         brand: params.brand, rubric_version: "hl.v1"}
  out = llm_json("highlights_rubric_package.v1", req, schema=RubricOut, temperature=0.3)
  for o in out:
    c = by_id(batch, o.cand_id)
    c.llm = o.scores; c.payoff = o.payoff_present; c.reason = o.reason
    apply_trims(c, o)                                   # adjust ranges by whole sentences; drop -> multi-range
    c.cold_open_hint = o.cold_open_candidate; c.packaging_draft = o.packaging
  return batch
```

`profile_brief(p)` is the profile slice from [platform-profiles.md](../features/publish-metadata/platform-profiles.md#config-shape): `{key, title.max_chars, caption.max_chars, caption.show_chars, hashtags.max, hook.window_s, hook.on_screen_text_max_words, voice}`.

## Fusion

```text
function fuse(c):
  L = c.llm
  llm = 0.30*L.hook + 0.25*L.value + 0.20*L.flow + 0.15*L.standalone + 0.10*L.trend
  sig = 0.35*pos(c.sig.energy_z) + 0.25*c.sig.laughter + 0.15*c.sig.face_engagement
      + 0.15*c.sig.visual_salience + 0.10*speech_rate_fit(c)
  pen = 2*c.sig.offtopic_ratio + 3*(not c.payoff) + 1.5*c.sig.dead_air_ratio + 2*starts_mid_thought(c)
  raw = 0.75*llm + 2.5*sig - pen
  score = round(99 * sigmoid((raw - 5.5) / 1.3))
  sub = {k: round(L[k] * 9.9) for k in ["hook", "flow", "value", "trend", "standalone"]}
  return score, sub

signals(c):  # computed over c.ranges, from cached artifacts
  energy_z        = mean z-score of short-term loudness vs whole-source distribution
  laughter        = max over windows of laughter/applause prob (PANNs), 0..1
  face_engagement = share of frames with a frontal face × mean expression intensity
  visual_salience = mean visual-track shot salience
  offtopic_ratio  = share of speech time in shots with speech.talk_offtopic and no topic match
  dead_air_ratio  = silence > 700 ms total / duration
  speech_rate_fit = 1 - |wpm - 165| / 165, clamped 0..1
```

## Selection

```text
function select(scored, count, src_min):
  limit = count == "auto" ? min(30, max(3, floor(src_min / 3))) : count
  floor_ = count == "auto" ? 60 : 0
  acc = []; per_seg = counter()
  for c in sort_desc(scored, by=score):
    if c.score < floor_: break
    if any(t_iou(c, a) > 0.3 for a in acc): continue
    if any(cos(embed(text(c)), embed(text(a))) > 0.85 for a in acc): continue
    if per_seg[c.seg] >= 3 and len(acc) < limit - 1: continue
    acc.append(c); per_seg[c.seg] += 1
    if len(acc) == limit: break
  return acc
```

## Boundary snapping

```text
function snap_boundaries(c, A, dur):
  for r in c.ranges:
    w0 = first_non_filler_word(A.transcript, r.start)          # drop leading um/so/yeah
    r.start = max(w0.start - 0.08, prev_word_end(w0) + 0.03)
    wl = last_word(A.transcript, r.end)
    tail = silence_after(wl) clamp [0.25, 0.6]
    r.end = wl.end + tail
    if A.laughter.active(r.end):
      ext = laughter_end(r.end)
      r.end = (ext - r.end <= 2.0) ? ext + 0.15 : laughter_start(r.end) - 0.05
  merge_ranges_with_gap_lt(c.ranges, 3.0)                        # small drops are not worth a jump
  c.ranges = c.ranges[:3]
  c.duration_s = sum(r.dur for r in c.ranges)
  c.platform_fit = {p: fit(c.duration_s, p.duration) for p in profiles}
  c.joins = [{at: cumulative_end(i), treat: "punch_in" if no_broll else "cutaway"} for i in 0..len-2]
```

## Reframe

```text
function plan_reframe(c, A, mode):
  path = []
  for shot in A.visual.shots_in(c.ranges):
    m = mode != "auto" ? mode :
        shot.events has screen_recording and A.faces.any(shot) ? "screen_cam" :
        A.asd.active_speakers(shot, window=4s) >= 2 ? "split" :
        shot.shot_size in ["wide", "extreme_wide"] and not A.faces.any(shot) ? "fit" : "fill"
    if m == "fill":
      target = A.asd.active_face_box(shot) or saliency_box(shot)
      path += smooth_crop(target, aspect=9/16, deadzone=0.06, max_pan_w_per_s=0.6,
                          hard_cut_if_jump>0.25)             # center-active-speaker.md filter
    elif m == "split":  path += split_two(A.asd.top2_faces(shot))
    elif m == "screen_cam": path += stack(screen_box(shot), A.faces.main(shot), top_ratio=0.6)
    else: path += fit_blur_bg(shot)
  return {mode: summarize(path), crop_path_ref: store(path)}
```

## Hook overlay and cold open

```text
function plan_hook_overlay(c, A, profs):
  pk = c.packaging_draft[profs[0].key]
  win_end = min(max(p.hook.window_s[1] for p in profs) + 1.0, 3.0, first_sentence_end(c) + 0.3)
  box = place_text(top_band(0.18, 0.30), avoid=A.faces.boxes(c, 0, win_end), safe=union_safe_zone(profs))
  return {text: pk.hook.on_screen_text, start_s: 0, end_s: win_end, box, style_id: "hook_bold"}

function plan_cold_open(c):
  h = c.cold_open_hint
  if not h or c.llm.hook >= 8: return              # already hooks; no teaser
  c.cold_open = word_range(h)                        # 2–4 s
  c.prepend = [c.cold_open, transition("whip", frames=6)]
```

## B-roll

```text
function plan_broll(c, A):
  spots = static_stretches(c, A, min_s=8) ∪ c.joins ∪ concrete_noun_mentions(c, A.transcript)
  spots = thin(spots, min_gap_s=8)
  out = []
  for s in spots:
    q = s.noun or summary_noun(text_around(s))
    hit = query_visuals(c.source, query=q, exclude=c.ranges).top(1)
    if hit and hit.score >= 0.5: out.append({at_s: s.t, dur_s: 2.0, asset_ref: hit, source: "project"})
    elif st := stock_search(q, orientation="portrait").top(1): out.append({..., source: "stock"})
  return out
```

## Packaging finalize

```text
function finalize_packaging(c, prof, A, brand):
  draft = c.packaging_draft[prof.key]
  facts = clip_facts(c, A)       # claims from the clip's own words + its visual lines only
  v = validate_and_repair(to_variant(draft), prof, brand, facts)   # publish-metadata.md
  if not prof.title: v.cover_text = v.title                         # TikTok/Reels/FB: title → cover/comp name
  return ClipPackaging(platform=prof.key, profile_version=prof.version, title=v.title, hook=v.hook,
                       description=v.description, hashtags=v.hashtags, checks=v.checks, grounding=v.grounding)

on clip_bounds_edited(c):
  c.packaging = {}; c.packaging_draft = llm_rubric_and_package([c], ...)[0].packaging_draft
  for p: c.packaging[p] = finalize_packaging(...)
```

## Agent tool

```text
tool find_highlights({composition_id, platforms=["tiktok"], count=3, min_s?, max_s?, topic?})
  -> [{clip_id, score, ranges:[{start, end}], duration, title, hook, reason}]
  # compact; packaging details via get_clip(clip_id). The create-clips skill then:
  #   plan with these → approval → keep_clip(clip_id) creates the composition with layout/captions/hook overlay
```

## Visual-only fallback

```text
function visual_only_highlights(src, A, params, profs):
  peaks = local_maxima(0.5*A.visual.salience_curve + 0.3*A.audio.energy_z + 0.2*A.motion, min_dist=dur.min_s)
  windows = [expand_to_shots(p, dur) for p in peaks]
  # rubric with visuals only; packaging from visual lines; stats.low_grounding = true
```
