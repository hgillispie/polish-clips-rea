# Room tone on gap clips

## Input / output

```text
input:   project, track, gap clip (no media, duration G), neighbor clips, media files with transcripts
output:  playback/export audio segments that fill G with looped, faded room tone
```

## Gap detection

```text
function is_gap_clip(clip) -> bool:
  return clip.audio != null and clip.audio.media_file_id == null and clip.visual == null

function create_gap_clip(project, duration) -> Clip:
  return Clip(audio = {media_file_id: null, duration},
              room_tone = project.settings.room_tone_on_gap_clips == true)
```

## Room tone source: extract per file (ours) or request (Descript)

```text
function ensure_room_tone(project, file):
  if file.room_tone_file_id or file.room_tone_job_id or file.room_tone_requested: return
  if not file.has_audio or file.is_recording: return
  if file.is_multitrack: for f in file.tracks: ensure_room_tone(project, f); return
  file.room_tone_requested = true
  enqueue job room_tone(file)   # result -> file.room_tone_file_id

triggers:
  on transcript_ready(file)        if project.settings.room_tone_on_gap_clips
  on upload_complete(file)         if project.settings.room_tone_on_gap_clips
  on clip.room_tone set true       for neighbor_file(clip)
  on "apply to existing" (enable)  for every file

job room_tone(file) -> AudioFile:
  words   = transcript(file).words
  env     = loudness_envelope(file, hop = 10ms)            # dBFS
  # candidate spans: outside words with 150 ms guard, not inside music, not clipped
  spans   = complement(words.expand(0.15s), file.duration).filter(len >= 0.4s)
  spans   = spans.filter(s -> max(env[s]) < speech_floor(env) - 6dB)
  rank    = sort(spans, by = (median(env[s]), -len(s)))   # quietest, then longest
  take spans from rank until total >= 6s (or all)
  if total < 2s: fail "not enough non-speech audio"       # Descript also requires >= 2 s
  pcm     = concat(take, crossfade = 30ms)
  pcm     = make_loopable(pcm, crossfade = 250ms)          # end crossfades into start
  pcm     = normalize_to(pcm, median_rms(take))           # keep the original noise level
  return save(pcm, kind = "room_tone", default_gain = 1)
```

Descript does this on its server ("analyzes the transcribed files"). Ours is local and deterministic. A later "synthesize" step (a noise model trained on `take`) can replace `concat`.

## Which file a gap uses

```text
function room_tone_for_gap(project, track, gap) -> (AudioFile, gain) | null:
  if not gap.room_tone or track.suppress_room_tone: return null
  prev = previous_non_gap(track, gap); next = next_non_gap(track, gap)
  src  = first of [prev, next] where file(src).room_tone_file_id != null
  if src == null: return null
  rt   = file(file(src).room_tone_file_id)
  if rt.duration < 2s: return null
  if file(src).studio_sound.enabled and file(src).studio_sound.intensity == 1: return null
  gain = src.gain * rt.default_gain
  if 0 < file(src).studio_sound.intensity < 1: gain *= dry_share(file(src).studio_sound.intensity)
  if track.is_multitrack_mix: gain /= count(non_suppressed_tracks(track))
  return (rt, gain)
```

## Loop, fade, mix

```text
function expand_gap(project, track, gap, fades = true) -> [Segment]:
  r = room_tone_for_gap(project, track, gap)
  if r == null: return [Silence(gap.duration)]
  (rt, gain) = r
  edge  = min(1.0, gap.duration / 2)
  chunk = rt.duration - 2.0
  out = []; remaining = gap.duration; i = 0
  while remaining > 0:
    len = min(chunk, remaining)
    seg = Segment(file = rt, offset = edge, duration = len, gain = gain, id = gap.id + "-rt:" + i)
    if i > 0: seg.crossfade_in = 0.05                         # ours; Descript butt-joins
    if fades and i == 0:            seg.fade_in  = Fade(edge, linear, extends_outward = true)
    if fades and remaining == len:  seg.fade_out = Fade(edge, linear, extends_outward = true)
    out.append(seg); remaining -= len; i += 1
  return out
```

- `fades = false` for DAW/session exports, so editors there get clean edges.
- Room tone volume edits `rt.default_gain`, shared by every gap that uses that file. The inspector says so.

## Apply to existing

```text
function set_room_tone_on_all_gaps(project, on):
  for comp in project.compositions:
    for clip in comp.script_track.clips where is_gap_clip(clip):
      clip.room_tone = on
  if on: for f in project.media_files where not f.is_multitrack: ensure_room_tone(project, f)
```
