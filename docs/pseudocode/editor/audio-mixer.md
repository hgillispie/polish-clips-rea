# Audio mixer

Per-clip and per-track level control, simple filters, and a Studio Sound effect node. The mix is local. Descript's API has no gain, pan, EQ, or ducking fields (static). "Studio Sound" as a product name is Descript's; the effect node calls the open implementation in [../studio-sound.md](../studio-sound.md).

## Types

```text
AudioClipSettings
  gain_db         number            # default 0
  muted           boolean           # default false
  pan             number            # -1 left .. +1 right, default 0
  fade_in_seconds number            # default 0
  fade_out_seconds number           # default 0
  highpass_hz     number | null     # null = off
  lowpass_hz      number | null
  eq              EqBand[]          # peak bands; MVP stores them and does not render them
  effects         Effect[]          # ordered; first is closest to the source

EqBand
  kind            "peak"
  freq_hz         number
  gain_db         number
  q               number
  enabled         boolean

Effect
  id              string
  kind            "studio_sound"
  enabled         boolean
  backend         "deepfilter" | "rnnoise" | "ffmpeg_afftdn"
  strength        "low" | "medium" | "high"

Ducking
  id              string
  speech_track_id string
  music_track_id  string
  threshold_db    number            # default -24
  reduction_db    number            # default 12
  attack_ms       number            # default 20
  release_ms      number            # default 200
  enabled         boolean

Meter
  peak_dbfs       number
  rms_dbfs        number
```

`Timeline` gains an optional `ducking: Ducking[]`. The MVP mixer ignores the list and reports `ducking bypassed` if it is non-empty. The stub below is the later algorithm.

## Gain law

```text
function clip_gain_at(clip, t) -> number:
  a = clip.audio
  if a is null or a.muted or clip.track.muted:
    return 0
  local = t - clip.start_seconds
  env = 1
  if a.fade_in_seconds > 0 and local < a.fade_in_seconds:
    env = local / a.fade_in_seconds
  tail = clip.duration_seconds - local
  if a.fade_out_seconds > 0 and tail < a.fade_out_seconds:
    env = min(env, tail / a.fade_out_seconds)
  return db_to_lin(a.gain_db + clip.track.gain_db) * env

function pan_gains(pan) -> (left, right):
  # Constant-power. pan 0 => both ~0.707.
  angle = (pan + 1) * pi/4
  return (cos(angle), sin(angle))
```

Solo: if any audio track has `solo`, tracks without `solo` contribute silence. Clip mute is independent and always silences that clip.

## Effect node

```text
function apply_effects(clip, source_pcm) -> pcm:
  pcm = source_pcm
  for effect in clip.audio.effects:
    if not effect.enabled:
      continue
    if effect.kind == "studio_sound":
      key = cache_key(clip.media_id, clip.source_in, clip.source_out, effect)
      pcm = cache.get(key) or cache.put(key, enhance_pcm(pcm, effect))
  if clip.audio.highpass_hz is not null:
    pcm = biquad_highpass(pcm, clip.audio.highpass_hz, q=0.707)
  if clip.audio.lowpass_hz is not null:
    pcm = biquad_lowpass(pcm, clip.audio.lowpass_hz, q=0.707)
  if any eq band is enabled:
    report "peak EQ bypassed"
  return pcm
```

`enhance_pcm` is [../studio-sound.md](../studio-sound.md) `enhance` on a wav of this clip's source range, using `effect.backend` and `effect.strength`. The cache avoids re-running the model on every playhead scrub. Invalidating the cache entry when `backend`, `strength`, or the source range changes is required.

The polish pipeline's enhance stage, when it produces an `enhanced` asset, seeds the audio clip's `media_id` to that asset and leaves `effects` empty. The operator can instead keep the original media and add a `studio_sound` effect. Do not run both on the same clip (the seeder must not attach an effect when it already swapped in the enhanced file).

## Mix

```text
function mix_interval(composition, t0, t1, sample_rate) -> stereo pcm:
  n = round((t1 - t0) * sample_rate)
  acc = zeros(n, 2)
  solos = any audio track has solo
  for track in audio tracks:
    if solos and not track.solo:
      continue
    if track.muted:
      continue
    for clip in track.clips:
      if clip does not overlap [t0, t1]:
        continue
      pcm = read_source(clip, t0, t1)          # zeros inside skip ranges
      pcm = apply_effects(clip, pcm)
      (gl, gr) = pan_gains(clip.audio.pan)
      for i, t in samples:
        g = clip_gain_at(clip, t)
        acc[i, 0] += pcm[i] * g * gl
        acc[i, 1] += pcm[i] * g * gr
  return acc
```

Mono sources are duplicated into `pcm[i]` before pan. If the sum peaks above -0.1 dBFS, apply a limiter at -1.0 dBFS and record `limited` on the export report. Preview meters show the pre-limiter peak so the operator can see the clip.

## Meters

```text
function meter(samples) -> Meter:
  peak = max(abs(s) for s in samples)
  rms = sqrt(mean(s*s for s in samples))
  return {
    peak_dbfs: lin_to_db(peak),    # -inf when peak is 0
    rms_dbfs: lin_to_db(rms)
  }
```

The preview computes this on each audio block (about 50 ms) per audible track and for the master sum. UI wiring is in [ui-surface.md](ui-surface.md).

## Ducking stub (later)

```text
function apply_ducking(speech_track_pcm, music_pcm, duck, sample_rate) -> music_pcm:
  env = envelope_follower(speech_track_pcm, duck.attack_ms, duck.release_ms, sample_rate)
  for i in samples:
    if lin_to_db(env[i]) > duck.threshold_db:
      music_pcm[i] *= db_to_lin(-duck.reduction_db)
  return music_pcm
```

Not called by `mix_interval` in the MVP. Stored `Ducking` values round-trip in `polish.project.v1`.

## Errors

| Case | Behaviour |
| --- | --- |
| `highpass_hz` >= `lowpass_hz` when both are set | Reject the edit |
| Fade longer than the clip | Clamp the fade to the clip duration on write |
| Pan outside -1..1 | Clamp |
| Studio Sound model missing | Same fallback chain as studio-sound.md (`deepfilter` → `rnnoise` → `ffmpeg_afftdn`). Record the backend that ran |
| Effect cache decode mismatch | Drop the cache entry and recompute once |

No 402.
