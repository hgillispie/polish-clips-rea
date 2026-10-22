# Visual descriptions (pseudocode)

Spec: [../features/visual-descriptions/README.md](../features/visual-descriptions/README.md). All of this is **design**.

## Entry point

```text
function build_visual_track(media, transcript=null, opts) -> VisualTrack:
  key = (sha256(media), VLM_MODEL_ID, PROMPT_VERSION, opts.density)
  if cache.has(key): return apply_overrides(cache.get(key), media.id)

  shots = detect_shots(media)                       # [{start_s, end_s, hard_cut}]
  shots = merge_short(shots, min_s=0.4) |> split_long(max_s=20, media)
  local = parallel_map(shots, s -> local_signals(media, s))
  frames = parallel_map(shots, s -> sample_frames(media, s, local[s], opts.density))

  est = estimate_cost(frames)
  if opts.budget_cents and est.cents > opts.budget_cents and not opts.confirmed:
    return VisualTrack(status="pending", estimate=est)        # UI asks

  order = priority_order(shots, transcript)          # wordless, then off-topic guess, then rest
  track = VisualTrack(status="partial", shots=[], coverage=[])
  spent = 0
  for batch in chunk(order, 8):
    if opts.budget_cents and spent >= opts.budget_cents: break
    prev_caption = track.last_caption_before(batch[0])
    out = vlm_describe(batch, frames, transcript, prev_caption)   # JSON per shot
    for s in batch:
      shot = merge_local_and_vlm(s, local[s], out[s.id])
      shot.speech = speech_relevance(shot, transcript)
      track.shots.insert_sorted(shot); track.coverage.add(s.range)
    spent += out.cost_cents
    emit_progress(track.coverage_ratio())
  smooth_offtopic(track.shots, window=3)
  track.status = "done" if track.coverage_ratio() == 1 else "partial"
  index_track(media.id, track)
  cache.put(key, track)
  return apply_overrides(track, media.id)
```

## Shots and sampling

```text
function detect_shots(media):
  if has_gpu(): return transnetv2(decode(media, fps=25, size=(48,27)), threshold=0.5)
  return pyscenedetect_adaptive(media, adaptive_threshold=3.0, min_scene_len_frames=10)

function split_long(shots, max_s, media):
  out = []
  for s in shots:
    if s.dur <= max_s: out.append(s); continue
    sig = embedding_change_curve(media, s, step_s=1.0)      # 1 - cos(siglip(t), siglip(t-1))
    cuts = peaks(sig, min_distance_s=6, top=ceil(s.dur / max_s) - 1)
    out += split_at(s, cuts or evenly(s, max_s))
  return out

function sample_frames(media, shot, local, density):
  rate = {sparse: 1/8, standard: 1/4, dense: 1/2}[density]
  n = clamp(1 + floor(shot.dur * rate), 1, 6)
  times = evenly_spaced(shot, n, inset=0.15)
  times += local.motion_peaks[:2] + local.text_likely[:2]
  frames = decode_at(media, times, max_side=768)
  return dedupe(frames, by=siglip_cosine > 0.95)
```

## Local signals (no LLM)

```text
function local_signals(media, shot):
  f = decode(media, shot, fps=6, max_side=320)
  flow = sparse_flow(f)                                    # LK on good features
  H = [homography(flow[i]) for i]
  camera = classify_motion(H)  # static if |translation|,|zoom| tiny; pan/tilt by axis; zoom by scale; handheld if jitter high
  return {
    camera,
    quality: { blur: 1 - norm(var_laplacian(f)), exposure: clip_fraction(f), shaky: jitter(H), frozen: frame_diff(f) < eps },
    faces: face_detector(f[::3]) |> summarize,
    motion_peaks: peak_times(frame_diff_energy(f)),
    text_likely: peak_times(edge_density(f)),
    embedding: mean(siglip(f[::3]))
  }
```

## VLM call

The prompt is ours and lives in the repo. Never paste a vendor's prompt. The schema below is what is sent as `response_schema`:

```text
ShotDescription = {
  shot_id: string,
  caption: string (<= 90 chars, present tense, concrete nouns, no identity guesses),
  events: [{ t_start: number (s from shot start), t_end: number, kind: enum, text: string }],
  entities: string[], setting: string, shot_size: enum, on_screen_text: string[],
  salience: number 0..1, content_flag: "none" | "sensitive" | "unsafe"
}

function vlm_describe(batch, frames, transcript, prev_caption):
  parts = [system_instructions_v(PROMPT_VERSION),
           "Previous shot: " + (prev_caption or "none")]
  for s in batch:
    parts += ["Shot " + s.id + " " + fmt(s.start_s) + "–" + fmt(s.end_s),
              "Speech during shot: " + (transcript.text_in(s.range) or "(none)")[:400]]
    parts += frames[s.id] as images(resolution="low" if s.dur < 3 else "medium")
  resp = model_router.call("vlm.describe", parts, schema=[ShotDescription], temperature=0.2)
  return validate_or_retry(resp, max_retries=1)       # drop shots that fail the schema twice; mark them failed
```

## Merge and relevance

```text
function merge_local_and_vlm(s, local, d):
  shot = Shot(id=stable_id(s), start_s=s.start_s, end_s=s.end_s, keyframe_s=mid(s),
              caption=d.caption, events=to_abs_time(d.events, s.start_s),
              entities=d.entities, setting=d.setting, on_screen_text=d.on_screen_text,
              camera=local.camera, shot_size=d.shot_size, quality=local.quality,
              faces=local.faces, salience=d.salience)
  if d claims camera motion that disagrees with local.camera: shot.low_confidence = true
  return shot

function speech_relevance(shot, transcript):
  words = transcript.text_in(shot.range) if transcript else ""
  if len(words.split()) < 3: return {wordless: true, relevance: null, talk_offtopic: false}
  r = cos(text_embed(words), text_embed(shot.caption + " " + join(e.text for e in shot.events)))
  return {wordless: false, relevance: r, talk_offtopic: r < 0.25}

function smooth_offtopic(shots, window):
  for i, s in enumerate(shots):
    neigh = [x.speech.talk_offtopic for x in shots[i-1 .. i+1] if not x.speech.wordless]
    s.speech.talk_offtopic = majority(neigh)
```

## Index and query

```text
function index_track(media_id, track):
  for s in track.shots:
    upsert(vectors, id=s.id, media_id, kind="shot", start_s, end_s,
           text_vec=text_embed(s.caption + " " + join(s.entities) + " " + join(s.on_screen_text)),
           image_vec=s.embedding, bm25_doc=s.caption + entities + on_screen_text + events.text)
    for e in s.events: upsert(vectors, id=s.id+":"+e.idx, kind="event", ..., text_vec=text_embed(e.text))

tool query_visuals({media_id?, composition_id?, range?, query?, kinds?, max_tokens=1500}):
  scope = resolve_scope(media_id, composition_id, range)       # composition → source ranges via timeline
  if query:
    hits = hybrid_search(query, scope, k=10, alpha=0.6)        # 0.6 vector + 0.4 BM25 (normalized)
    return lines(hits)
  shots = shots_in(scope, kinds)
  text = join(line(s) for s in shots)
  if tokens(text) > max_tokens:
    return {status: "oversized", estimated_tokens: tokens(text), max_tokens,
            hint: "narrow range; densest stretch is " + densest_range(shots)}
  return text

function line(s):  # composition time when scope was a composition
  return "[" + t0 + "–" + t1 + "] " + s.shot_size + " · " + s.camera + ' · "' + s.caption + '"'
         + (s.on_screen_text ? ' · text:"' + s.on_screen_text[0] + '"' : "")
         + (s.speech.talk_offtopic ? " · talk≠picture" : "") + (s.speech.wordless ? " · no speech" : "")
```

## Script markdown integration

```text
function script_markdown(comp, include_visuals="wordless_only"):
  for block in comp.blocks():
    if block.is_wordless or (include_visuals == "all"):
      emit("> [visual " + range + "] " + join(captions_in(block.range), " / "))
    if include_visuals != "none" and block.offtopic_ratio > 0.6:
      emit("> [visual, talk off-topic] " + join(captions_in(block.range), " / "))
    emit(block.words_markdown)
```

## Errors

| Case | Result |
| --- | --- |
| No video stream | `failed: "no video"`. Images go through the single-shot path |
| VLM 429/5xx | Back off exponentially, at most 3 tries per batch. Then mark the batch failed and keep the others |
| Budget hit | `status = partial`; `coverage` shows what is done |
| Schema violation twice | That shot is `failed`; the local signals are still stored |
