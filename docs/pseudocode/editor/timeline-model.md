# Timeline model

Time is seconds on the **composition clock**. Source media keeps its own clock (`source_in`, `source_out`). Ignoring a word does not rewrite source timestamps in the transcript; the timeline playback skips that span. See [../transcript-model.md](../transcript-model.md).

## Types

```text
Track
  id              string
  kind            "video" | "audio" | "caption" | "overlay"
  name            string
  index           integer          # 0 = bottom of the visual stack
  muted           boolean
  solo            boolean
  gain_db         number           # track fader, default 0
  pan             number           # -1..1, audio tracks only, default 0
  clips           Clip[]           # sorted by start_seconds

Clip
  id              string
  track_id        string
  kind            "media_video" | "media_audio" | "caption" | "text" | "shape" | "image"
  name            string
  start_seconds   number           # composition clock, >= 0
  duration_seconds number          # > 0
  source_in       number           # media clock; 0 for generated clips
  source_out      number           # source_in + duration, unless the clip is sped
  speed           number           # default 1; duration = (source_out - source_in) / speed
  media_id        string | null
  link_group      string | null    # clips that ripple together
  transcript_link
    transcript_id string
    word_ids      string[]         # words this clip covers, source order
  skip_ranges     SkipRange[]      # composition-clock gaps inside the clip (from ignore)
  layer           VisualLayer | null
  audio           AudioClipSettings | null
  caption_style_id string | null
  cues            Cue[] | null     # caption clips

SkipRange
  id              string
  start_seconds   number           # composition clock, clipped to the clip
  end_seconds     number
  reason          "filler" | "retake" | "manual" | "silence"
  word_ids        string[]
```

`VisualLayer` is in [layers.md](layers.md). `AudioClipSettings` is in [audio-mixer.md](audio-mixer.md).

## Placement rules

```text
function place_clip(track, clip):
  if clip.duration_seconds <= 0:
    fail "clip duration must be positive"
  if clip.source_out <= clip.source_in and clip.media_id is not null:
    fail "source out must be after source in"
  if overlaps(track, clip) and track.kind == "caption":
    fail "caption clips on one track cannot overlap"
  # video and audio tracks may overlap; the later clip in track.clips
  # (higher array index) wins while both are active. See layers.md.
  track.clips.append(clip)
  sort track.clips by start_seconds, then by array order
```

Composition duration is the max of each clip's `start_seconds + duration_seconds`, ignoring skip ranges (skips shorten playback, not the authored span, until a ripple closes them — [selection-and-edits.md](selection-and-edits.md)).

## Stacking

Visual paint order, bottom to top:

1. Tracks in increasing `index`, only `video` and `overlay`.
2. Within a track, clips in array order. An overlapping later clip covers an earlier one where their rects intersect, after transforms.
3. The caption track paints after every video and overlay track when burn-in or preview captions are enabled. A caption track does not paint if the operator is exporting sidecars only.

Audio tracks do not paint. Their mix order is in [audio-mixer.md](audio-mixer.md).

## Sequences

```text
SequenceRef
  composition_id   string
```

A clip with `media_id` pointing at a composition is a nested sequence. Render would composite that composition into the clip's slot, then apply the parent transform.

MVP: `place_clip` rejects `media_id` values that are composition ids and returns "nesting is not enabled". The field stays in the model so a later renderer can accept it without a migration.

## Scenes

A scene is a marker pair plus a label, not a separate document:

```text
function scene_spans(timeline) -> Span[]:
  times = [0] + [m.time_seconds for m in timeline.markers] + [composition_duration]
  return consecutive pairs as spans
```

Scenes do not change playback. They are labels for the operator and for a later "export this scene" command.

## Invariants

- Clip ids are unique inside the composition.
- `start_seconds >= 0`.
- Skip ranges lie inside `[start_seconds, start_seconds + duration_seconds)` and do not overlap each other.
- A caption clip's cues lie inside the clip's playback (after skips).
- `transcript_link.word_ids` are a contiguous source-order span on that transcript.
- Linked clips share one `link_group` string. The MVP seeder uses the video clip id as that string.
