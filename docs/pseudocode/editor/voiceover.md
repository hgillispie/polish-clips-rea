# Voiceover

A voiceover is speech on its **own audio track**, placed against the composition clock. It is not a transcript ignore, and it is not a voice clone. Correcting a line by speaking it again is the default; a synthetic voice needs the consent gate in [../voice-consent.md](../voice-consent.md).

Gain, pan, and fades are [audio-mixer.md](audio-mixer.md) `AudioClipSettings`. Ducking under dialogue is optional and off unless the operator turns it on.

## Types

```text
VoiceoverTrack
  track_id              string          # Track.kind = "audio"
  role                  "voiceover"
  duck_under_dialogue   boolean         # default false
  dialogue_track_id     string | null   # the speech track to duck against

VoiceoverTake
  id                    string
  media_id              string          # wav or the audio of a video file
  recorded_at           string          # ISO 8601, local clock
  playhead_seconds      number          # composition time where record started
  punch_in              Range | null    # if set, this take replaces that range
  source                "record" | "import"

Range
  start_seconds         number
  end_seconds           number
```

The clip that lands on the timeline is an ordinary audio `Clip` with `transcript_link` left null until a later ASR pass. The polish transcript of the main camera is not rewritten when a voiceover is added.

## Record

```text
function arm_voiceover(composition) -> VoiceoverTrack:
  track = the track with role "voiceover" or a new Track(kind="audio", name="Voiceover")
  track.role = "voiceover"
  return track

function record_voiceover(composition, track, from_time | null) -> VoiceoverTake:
  t0 = from_time if from_time is not null else composition.playhead
  if t0 < 0:
    fail "playhead is before 0"
  stream = getUserMedia({ audio: true, video: false })
  # Playback of the composition continues so the speaker can hear dialogue.
  # Monitor must not feed the speakers back into the mic (operator uses headphones).
  samples = capture_until_stop(stream)
  if duration(samples) < 0.05:
    fail "recording too short"
  asset = write_wav(samples, sample_rate=48000, channels=1)
  take = VoiceoverTake(media_id=asset.id, playhead_seconds=t0, punch_in=null, source="record")
  place_take(composition, track, take)
  return take
```

Sync to the playhead means `clip.start_seconds = take.playhead_seconds`. The file's `source_in` is 0. If the take would run past the composition end, the composition duration grows to fit. It does not trim the performance.

## Import

```text
function import_voiceover(composition, track, path, at_time) -> VoiceoverTake:
  asset = ingest_local(path)                  # audio, or the audio stream of a video
  if asset has no audio:
    fail "file has no audio"
  take = VoiceoverTake(media_id=asset.id, playhead_seconds=at_time, source="import")
  place_take(composition, track, take)
  return take

function place_take(composition, track, take):
  clip = Clip(
    kind="media_audio",
    media_id=take.media_id,
    start_seconds=take.playhead_seconds,
    duration_seconds=asset_duration(take.media_id),
    source_in=0,
    source_out=asset_duration(take.media_id),
    audio=AudioClipSettings()                 # gain 0 dB, fades 0
  )
  if take.punch_in is not null:
    replace_range(track, take.punch_in, clip)
  else:
    place_clip(track, clip)                   # timeline-model.md; overlaps allowed
```

Imported video does not become a visual layer. Use [overlays.md](overlays.md) for a picture.

## Punch-in

Punch-in records or imports over an existing range and **replaces** that span on the voiceover track. Audio outside the range stays.

```text
function punch_in(composition, track, range, source) -> VoiceoverTake:
  if range.end_seconds <= range.start_seconds:
    fail "empty punch-in"
  take = record or import, with punch_in = range
  # place_take calls replace_range
  return take

function replace_range(track, range, new_clip):
  survivors = []
  for clip in track.clips:
    overlap = intersection(clip_span(clip), range)
    if overlap is empty:
      survivors.append(clip)
      continue
    # Keep the left stub and the right stub. Source clocks follow the cut.
    if clip.start_seconds < range.start_seconds:
      left = copy(clip)
      left.duration_seconds = range.start_seconds - clip.start_seconds
      left.source_out = left.source_in + left.duration_seconds * left.speed
      survivors.append(left)
    if clip.start_seconds + clip.duration_seconds > range.end_seconds:
      right = copy(clip)
      delta = range.end_seconds - clip.start_seconds
      right.start_seconds = range.end_seconds
      right.source_in = clip.source_in + delta * clip.speed
      right.duration_seconds = clip.duration_seconds - delta
      survivors.append(right)
  new_clip.start_seconds = range.start_seconds
  # If the new performance is longer than the range, ripple clips that start
  # at or after range.end on this track only. Dialogue tracks do not move.
  extra = new_clip.duration_seconds - (range.end_seconds - range.start_seconds)
  if extra > 0:
    for clip in survivors:
      if clip.start_seconds >= range.end_seconds:
        clip.start_seconds += extra
  survivors.append(new_clip)
  track.clips = sort by start_seconds
```

Punch-in does not set `Word.ignored` on the main transcript. If the operator also wants the original line silenced, they mute or trim that range on the dialogue track themselves.

## Levels

The inspector edits `clip.audio` ([ui-surface.md](ui-surface.md)): `gain_db`, `fade_in_seconds`, `fade_out_seconds`, `muted`, `pan`. A 10 ms fade-in and fade-out are applied on punch-in edges inside `replace_range` when the operator has not set a fade, so the splice does not click. Record that default on the clip.

## Ducking

When `duck_under_dialogue` is true and `dialogue_track_id` is set, export and preview call `apply_ducking` from [audio-mixer.md](audio-mixer.md) with the dialogue track as the sidechain and this voiceover track as the program being reduced. Default thresholds stay the ones on `Ducking`. Other music ducking stays off until an operator adds a `Ducking` row.

```text
function voiceover_duck(composition, track) -> Ducking | null:
  vt = voiceover settings for track
  if not vt.duck_under_dialogue:
    return null
  return Ducking(
    speech_track_id=vt.dialogue_track_id,
    music_track_id=track.id,
    enabled=true
  )
```

`mix_interval` runs that duck after the voiceover clip gains and before the master sum. Dialogue is not reduced.

## Errors

| Case | Behaviour |
| --- | --- |
| Mic permission denied | Fail before a file is written |
| No audio device | Fail with "no input" |
| Punch-in range outside the composition | Clamp to `[0, duration]` if any overlap remains; fail if the clamp is empty |
| Import longer than 2 hours | Reject. The operator can trim outside the app |
| Feedback risk (no headphone hint) | Record anyway. The UI warns once |

No 402. Recording is local.
