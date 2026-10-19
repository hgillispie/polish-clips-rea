# Align clips by waveform

Place two recordings of the **same scene** on parallel tracks so their audio matches in time. The operator can then switch which video is visible. This is multicam sync, not Descript's Automatic Multicam.

Descript's help describes **Automatic Multicam** as detecting speaker changes in a multi-track sequence, creating scenes, and switching the angle to whoever is talking (static, help index, 2026-10-19). That is a cut decision. This file only finds an offset. It does not decide who is on screen.

No Descript source is involved. The algorithms are standard signal processing.

## Input / output

```text
input:
  clip_a          Clip            # has audio; treated as the reference
  clip_b          Clip            # the clip to move
  options
    max_offset_seconds   number   # default 30; search window
    drift            boolean      # default false; allow a small resample
    max_drift_ratio  number       # default 0.005 (0.5%)
output:
  group           MulticamGroup
  report
    offset_seconds     number     # added to clip_b.start_seconds
    score              number     # correlation peak, 0..1
    drift_ratio        number     # 0 if drift is off
    method             string

MulticamGroup
  id              string
  reference_id    string          # clip_a
  members         { clip_id, offset_seconds, score }[]
  active_id       string          # which video is shown; others are muted visually
```

## Envelope

```text
function envelope(clip) -> float[]:
  pcm = mix_to_mono(read_all_audio(clip), sample_rate=8000)
  # 20 ms mean absolute value. Speech and claps both survive.
  hop = 160
  env = []
  for i in 0 .. len(pcm) step hop:
    env.append(mean(abs(pcm[i : i + hop])))
  env = highpass_subtract_mean(env)
  return env
```

8000 Hz and a short hop keep the search cheap. The original media is not resampled unless drift correction is on.

## Offset

Normalized cross-correlation over the allowed lag. GCC-PHAT on the same envelopes is the alternative when room noise makes the plain peak flat; try plain first, and use GCC-PHAT if the best score is under 0.35.

```text
function align_pair(clip_a, clip_b, options) -> report:
  ea = envelope(clip_a)
  eb = envelope(clip_b)
  max_lag = round(options.max_offset_seconds / 0.020)
  (lag, score) = best_normalized_correlation(ea, eb, max_lag)
  if score < 0.35:
    (lag, score) = gcc_phat_lag(ea, eb, max_lag)
    method = "gcc-phat"
  else:
    method = "cross-correlation"
  if score < 0.2:
    fail "no reliable overlap; place the clips by hand"
  offset = lag * 0.020
  drift_ratio = 0
  if options.drift:
    drift_ratio = estimate_drift(ea, eb, lag, options.max_drift_ratio)
  apply_offset(clip_b, offset, drift_ratio)
  return report(offset, score, drift_ratio, method)

function best_normalized_correlation(a, b, max_lag) -> (lag, score):
  best = (0, -1)
  for lag in -max_lag .. max_lag:
    s = dot(a, shift(b, lag)) / (norm(a) * norm(shift(b, lag)))
    if s > best.score:
      best = (lag, s)
  return best
```

`shift` zero-pads. A positive lag means clip B's audio happens later than A, so B's `start_seconds` decreases (it must begin earlier on the timeline) by `offset`. Sign is fixed in tests: a known 1.0 s delay of B must produce `offset_seconds = -1.0` on B when A is the reference.

```text
function apply_offset(clip, offset_seconds, drift_ratio):
  clip.start_seconds = max(0, clip.start_seconds + offset_seconds)
  if drift_ratio != 0:
    # speed = 1 + drift_ratio. duration and source_out follow timeline-model.md.
    clip.speed = 1 + drift_ratio
    clip.duration_seconds = (clip.source_out - clip.source_in) / clip.speed
```

If `start_seconds` would go below 0, shift the **reference** later by the overflow instead, and store that on the group so both members stay non-negative.

## Drift

Only when `options.drift` is true. Split B's envelope into two halves, estimate a lag on each against A, and convert the lag change into a speed ratio. Clamp to `± max_drift_ratio`. If the two half-lags disagree by more than the clamp, leave speed at 1 and set `drift_ratio` 0 with method note `drift rejected`. Mild clock drift between two devices is the target. A different edit of the scene is not.

## Group and angle switch

```text
function make_group(clip_a, clip_b, report) -> MulticamGroup:
  group = MulticamGroup(reference_id=clip_a.id, active_id=clip_a.id, members=[
    { clip_a.id, 0, 1 },
    { clip_b.id, report.offset_seconds, report.score }
  ])
  clip_a.multicam_group_id = group.id
  clip_b.multicam_group_id = group.id
  # Parallel tracks: if they share a track, move B onto a new video track
  # with the same index family so both exist. Active clip paints; inactive
  # video clips in the group are skipped by composite_frame.
  return group

function switch_angle(group, clip_id):
  if clip_id not in group.members:
    fail "clip is not in the group"
  group.active_id = clip_id
```

Audio: play the active clip's audio. Mute the other members' audio while they are inactive so two mics do not double. The operator can solo a different mic without changing the picture by setting `audio_from = clip_id` on the group. Default `audio_from` is `active_id`.

`composite_frame` skips a video clip whose `multicam_group_id` is set and whose id is not `active_id`.

## Build options

| Method | When |
| --- | --- |
| Normalized cross-correlation of the energy envelope | Default. No extra library |
| GCC-PHAT on the same envelopes | Fallback when the peak is weak |
| Chromaprint-style fingerprint (open Chromaprint / acoustid implementations) | Optional second opinion for music-heavy takes. Compare fingerprint match time to the envelope offset; if they disagree by more than 200 ms, show both and let the operator pick |
| Descript Automatic Multicam | A different feature (who is on screen). Not an implementation of this offset |

## Errors

| Case | Behaviour |
| --- | --- |
| Clip has no audio | Fail that pair |
| Score under 0.2 | Fail and leave positions unchanged |
| Offset search hits the window edge | Warn "offset may lie outside the window"; still apply if score ≥ 0.2 |
| Drift rejected | Align with offset only |

No 402.
