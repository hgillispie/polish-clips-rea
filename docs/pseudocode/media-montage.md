# Media montage (pseudocode)

Spec: [../features/media-montage/README.md](../features/media-montage/README.md). All of this is **design**.

```text
function montage(media, p) -> Montage:
  mus = p.music ? analyze_music(p.music) : synthetic_grid(p.vibe, p.target_s)
  curve = p.curve or pacing_curve(mus, p.vibe)
  slots = make_slots(mus, curve, p.target_s)
  pool = build_pool(media, p.aspect, excludes=p.excludes)
  plan = assign(slots, pool, p.order, pins=p.pins)
  for s in plan: if s.asset.kind == "image": s.kenburns = ken_burns(s.asset, s.dur, p.vibe, s.index)
                 else: s.in_s = align_action(s.asset, s.dur, s.t0, mus)
  plan_transitions(plan, mus, p.vibe)
  return assemble_montage(plan, mus, p)
```

## Music

```text
function analyze_music(track):
  beats, downbeats = beat_this(track) or madmom_dbn(track) or librosa_beat_track(track)
  tempo = 60 / median(diff(beats))
  ssm = self_similarity(stack(chroma(track), mfcc(track)), per_beat=beats)
  bounds = peaks(novelty(ssm, kernel=16 beats), min_dist=8 beats)
  energy = per_beat(normalize(onset_strength(track) + rms(track)))
  sections = label_sections(bounds, energy)            # low/med/high energy; "drop" = sharp energy rise after low section
  return {beats, downbeats, tempo, sections, energy}

function pacing_curve(mus, vibe):
  base = {calm: 6, balanced: 3, energetic: 1.5}[vibe]
  return [ {t: b, beats_per_shot: quantize(base * (1.5 - mus.energy[b]), [0.5, 1, 2, 4, 8])} for b in mus.beats ]
```

## Slots

```text
function make_slots(mus, curve, target_s):
  t = start_of_best_section_window(mus, target_s)        # contiguous; ends on a section/phrase end
  out = []
  while t < t_start + target_s:
    n = curve.at(t).beats_per_shot
    end = beat_after(t, n)
    if n >= 2: end = snap_to(downbeats, end, max_shift_beats=1)
    if section_boundary_between(t, end): end = that_boundary
    out.append(Slot(t0=t, t1=end, energy=mean(mus.energy[t:end]), section=section_at(t)))
    t = end
  return out
```

## Pool

```text
function build_pool(media, aspect, excludes):
  pool = []
  for m in media:
    if m.kind == "image":
      q = image_quality(m)
      if q.ok: pool.append(Cand(m, kind="image", quality=q.score, aesthetic=aesthetic(m), interest=faces_interest(m),
                                emb=siglip(m), t=capture_time(m), orient=orientation_fit(m, aspect)))
      continue
    for shot in shots(m):                                # visual track or TransNetV2
      for w in best_windows(shot, min_s=0.5, max_s=6):   # argmax sharpness*motion_interest*faces
        q = quality(w)                                   # blur, exposure, shake
        if q.blur > 0.4 or q.shake > 0.5 or q.exposure_clip > 0.3: continue
        pool.append(Cand(m, w, kind="video", quality=q.score, aesthetic=aesthetic(mid_frame(w)),
                         interest=0.5*faces_interest(w) + 0.3*motion(w) + 0.2*salience(w),
                         motion=motion(w), emb=siglip(mid_frame(w)), t=capture_time(m) + w.in_s,
                         orient=orientation_fit(m, aspect), dur=w.dur))
  return [c for c in pool if not excluded(c, excludes)]
```

## Assignment

```text
function fit(slot, c):
  if c.kind == "video" and c.dur < slot.dur * 0.9: return -INF
  f = c.quality * (0.4 + 0.6 * c.aesthetic) * (0.3 + 0.7 * c.interest)
  f *= 1 - abs(c.motion - slot.energy) * 0.5              # match motion to energy
  f *= c.orient
  return f

function assign(slots, pool, order, pins):
  place_pins(slots, pins, order)
  if order == "chronological":
    P = sort(pool, by=t)
    # DP over (slot i, last pool index j): best total with monotone time; variety check against previous pick
    dp[i][j] = max_{k<j} dp[i-1][k] + fit(slots[i], P[j]) - variety_pen(P[k], P[j], history)
    return backtrack(dp)                                 # O(S·N²); prune with N ≤ 400 top candidates by fit
  used = {}
  for i, s in enumerate(slots) if not s.locked:
    best = argmax_{c not in used} fit(s, c) - variety_pen(prev(i), c, window=last 5 picks)
                                           + 0.3 * lookahead(i, c, depth=3)
    s.asset = best; used.add(best)
  return local_swaps(slots, iters=300)

function variety_pen(prev, c, window):
  pen = 0
  if prev and cos(prev.emb, c.emb) > 0.85: pen += 1.0
  if count(w.source == c.source for w in window) >= 2: pen += 0.6
  if prev and scene_type(prev) == scene_type(c): pen += 0.2
  return pen
```

## Ken Burns

```text
function ken_burns(img, dur, vibe, idx):
  z = {calm: 1.12, balanced: 1.18, energetic: 1.25}[vibe]
  focus = face_union_box(img) or saliency_peak_box(img)
  full = fit_rect(img, aspect)
  tight = scale_rect_around(full, 1/z, center=focus.center)
  tight = keep_faces_inside(tight, faces(img))
  from_r, to_r = (idx % 2 == 0) ? (full, tight) : (tight, full)
  return {from_rect: from_r, to_rect: to_r, ease: "in_out_cubic", dur}

function align_action(asset, dur, t0, mus):
  peak = motion_peak_time(asset.window)                  # biggest motion/onset inside the window
  in_s = clamp(peak - dur/3, asset.window.in_s, asset.window.out_s - dur)
  return in_s
```

## Transitions and assemble

```text
function plan_transitions(plan, mus, vibe):
  for a, b in pairs(plan):
    if section_change(a, b) and vibe == "calm": t = {kind: "xfade", frames: 12}
    elif is_drop(b.t0, mus) and vibe == "energetic": t = {kind: "whip", frames: 6}
    else: t = {kind: "cut", frames: 0}
    a.transition = t

function assemble_montage(plan, mus, p):
  commit("Create montage"):
    comp = create_composition(aspect=p.aspect)
    for s in plan: add_layer(comp, s)                    # video range or image with kenburns keyframes
    add_music(comp, p.music, loudness=-14, fade_out_last_bar=true)
    if p.use_clip_audio: for s in plan if s.asset.audio_interest: duck_music(comp, s.t0, s.t1, -10)
  return Montage(...)
```
