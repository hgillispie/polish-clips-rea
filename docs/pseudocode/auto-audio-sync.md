# Auto audio sync (pseudocode)

Spec: [../features/auto-audio-sync/README.md](../features/auto-audio-sync/README.md). This replaces [editor/audio-waveform-align.md](editor/audio-waveform-align.md) for anything beyond one pair. Output feeds [automatic-multicam.md](automatic-multicam.md). All of this is **design**.

Sign convention (test it): `offset_s` is the clip's start on the session clock. If B's sound happens 1.0 s *later* in B's file than in master A's file, B starts 1.0 s *earlier*, so `offset_s(B) = -1.0`.

```text
SR_C = 8000; HOP = 0.010

function auto_sync(clips, opt) -> SyncResult:
  feats = {c: features(c) for c in clips if c.has_audio}         # cached by media sha
  hints = {c: read_hints(c) for c in clips}                       # timecode, file times, device_key
  pairs = candidate_pairs(feats, hints)                           # all pairs if n<=8 else landmark votes
  edges = []
  for (a, b) in pairs:
    e = match_pair(feats[a], feats[b], window_from_hints(hints[a], hints[b], opt))
    if e and e.conf >= 0.5: edges.append(e)
  sessions = connected_components(nodes=feats.keys(), edges)
  result = SyncResult()
  for comp in sessions:
    if len(comp) == 1: result.lone.append(comp[0]); continue
    master = choose_master(comp, feats, opt.master)
    placement = solve_offsets(comp, edges_within(comp), master)
    placement = apply_device_constraints(placement, hints)
    result.sessions.append(Session(master, placement))
  place_silent_and_lone(result, clips, hints)                     # timecode > visual > file time
  if not result.sessions: result.no_op_reason = "no_overlap" if len(feats) >= 2 else "not_enough_audio"
  return result
```

## Features

```text
function features(clip):
  x = resample(mono(clip.audio), SR_C)
  S = log(1 + 10 * mel_spectrogram(x, n_fft=512, hop=80, n_mels=40))
  onset = half_wave_rectify(diff(S, axis=time)).sum(axis=mel)    # spectral flux, 10 ms frames
  onset = (onset - moving_avg(onset, 1.0s)) / (moving_std(onset, 1.0s) + eps)
  return {onset, chroma: chroma_cqt(x, hop=80), landmarks: wang_landmarks(S), pcm8k: x,
          pcm48k_ref: clip.audio_ref, dur: len(x)/SR_C, snr: estimate_snr(x)}

function wang_landmarks(S):
  peaks = local_maxima(S, neighborhood=(15 frames, 7 bins), top_per_second=30)
  for p in peaks: for q in next peaks within 0.1–1.0 s and ±10 bins, up to 5:
    yield hash(p.bin, q.bin, q.t - p.t), p.t
```

## Pair matching

```text
function match_pair(A, B, win):
  # coarse: GCC-PHAT on onset envelopes, restricted lag window
  lags, r = gcc_phat(A.onset, B.onset, max_lag=win.max_lag_frames)
  cands = top_k_peaks(r, k=3, min_sep=0.5s)
  best = null
  for c in cands:
    fine = refine(A.pcm8k, B.pcm8k, c.lag * HOP, radius=0.050, sr=SR_C)
    fine = refine(load48k(A), load48k(B), fine.lag_s, radius=0.002, sr=48000)   # parabolic interp
    wins = window_lags(A, B, fine.lag_s, n=4)                                   # lag per quarter of overlap
    drift = ransac_line(wins)                                                    # lag(t) = a + b t
    spread = max_residual_ms(wins, drift)
    lm = landmark_vote_lag(A.landmarks, B.landmarks)                              # null if < 20 votes
    agree = lm is null or abs(lm - fine.lag_s) <= 0.020
    conf = logistic(w1*psr(fine) + w2*(spread <= 10) + w3*agree + w4*log(overlap_s(A,B,fine.lag_s)))
    if not best or conf > best.conf:
      best = Edge(a=A.id, b=B.id, lag_s=fine.lag_s, drift_ppm=drift.b*1e6, conf, overlap_s, spread)
  return best

function gcc_phat(x, y, max_lag):
  n = next_pow2(len(x) + len(y))
  X = rfft(x, n); Y = rfft(y, n)
  R = X * conj(Y); R = R / (abs(R) + 1e-12)                     # PHAT weighting
  r = fftshift(irfft(R, n))
  center = n // 2
  window = r[center - max_lag : center + max_lag + 1]
  return arange(-max_lag, max_lag + 1), window

function psr(fine):  # peak-to-sidelobe ratio
  side = fine.corr excluding ±5 ms around peak
  return (fine.peak - mean(side)) / (std(side) + eps)
```

`lag_s > 0` means B's content appears later in B's file than in A's, so `offset(B) - offset(A) = -lag_s`.

## Session solve

```text
function solve_offsets(nodes, edges, master):
  # unknown t_j per node, t_master = 0. Each edge: t_b - t_a = -lag_s, weight conf.
  loop up to 3:
    t = weighted_least_squares(nodes, edges, fixed={master: 0})
    res = {e: abs((t[e.b] - t[e.a]) + e.lag_s) for e in edges}
    bad = [e for e in edges if res[e] > 0.015]
    if not bad: break
    edges = edges - {argmax(res)}                   # drop worst, re-solve
  drift = {}
  for n in nodes != master:
    e = strongest_edge_to_master_path(n, edges)
    if abs(e.drift_ppm) > 5 and e.overlap_s > 600 and abs(e.drift_ppm) < 500: drift[n] = e.drift_ppm
  shift = -min(t.values()); for n: t[n] += shift      # nothing starts before 0 (prependSeconds)
  return {n: Placement(offset_s=t[n], speed=1 + drift.get(n, 0)/1e6,
                       conf=node_conf(n, edges), placed_by="audio") for n in nodes}

function choose_master(nodes, feats, pref):
  if pref != "auto": return pref
  score(n) = 2*norm(feats[n].snr) + norm(feats[n].dur) + (1 if is_external_recorder(n) else 0)
  return argmax(score)
```

## Silent and lone clips

```text
function place_silent_and_lone(result, clips, hints):
  for c in clips not placed:
    if hints[c].timecode and some session has timecode on a placed member:
      place(c, by="timecode")
    elif has_video(c) and (v := visual_sync(c, result)) and v.psr >= 6:
      place(c, by="visual", offset=v.offset)
    elif hints[c].file_time and same device lane exists:
      place(c, by="file_time")
    else:
      result.unplaced.append({clip: c, reason: c.has_audio ? "no shared sound" : "no audio"})

function visual_sync(c, result):
  e = frame_diff_energy(c, fps=30)          # flashes, claps, cuts
  for s in result.sessions: for m in s.members with video:
    lag, corr = gcc_phat(e, frame_diff_energy(m, fps=30), max_lag=from_file_time_or(120s))
    keep best by psr
```

## Apply

```text
function apply_sync(result, timeline):
  commit("Sync by audio"):
    for s in result.sessions:
      g = upsert SyncGroup(master_audio_clip_id=s.master)
      for p in s.placements:
        clip = timeline.clip(p.clip_id)
        clip.group_id = g.id; clip.source_speed = p.speed
        clip.start_on_group = p.offset_s
        clip.audio_muted = (p.clip_id != s.master)
        reanchor_transcript(clip.media_id, speed=p.speed)       # words stay attached to media time
  toast(summary(result))     # "Synced 4 clips in 2 sessions · drift corrected on GoPro (+38 ppm) · 1 not matched"

function nudge(group, clip_id, delta_s):     # arrow keys: ±1 frame, Shift: ±10 ms
  commit("Nudge sync"): m = group.member(clip_id); m.offset_s += delta_s; m.placed_by = "manual"
```

## Tests (must pass)

- Synthetic: offset +1.000 s → `offset(B) = -1.000 ± 0.001`.
- +200 ppm speed → drift detected within ±5 ppm.
- 0 dB SNR babble → conf ≥ 0.5.
- Three files where A–B and B–C overlap but A–C do not → all placed. Residual ≤ 2 ms.
- Two unrelated recordings → separate sessions, none placed against each other.
