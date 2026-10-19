# Editor overview

The editor is the canvas. The polish pipeline is a batch of transcript and media operations that can drop a result onto that canvas. Neither one clones the Descript web UI. These types are a product spec, not a trace of Descript's document format (the public API exposes projects and compositions, not this graph — **static** absence).

## How the pieces sit

```text
Polish pipeline                         Editor
  ingest, ASR                             Project
  filler ignore, retake ignore              compositions[]
  enhance (effect node or file)               Timeline
  Cue[] from non-ignored words                  tracks[] → clips
  optional burn-in                            Preview composite
                                              Inspector writes style and gain
```

The pipeline mutates a `Transcript` and may write a new media file. The editor displays that transcript beside a timeline and writes the same `ignored` flag back when the operator strikes a word. Export goes through [export-render.md](export-render.md), which calls [../caption-burnin.md](../caption-burnin.md) when burn-in is on.

## Types

```text
Project
  id                string
  name              string
  media             MediaAsset[]
  fonts             FontAsset[]          # caption-style.md
  styles            CaptionStyle[]
  transcripts       Transcript[]         # transcript-model.md
  compositions      Composition[]

Composition
  id                string
  name              string
  width             integer              # default 1920
  height            integer              # default 1080
  fps               number               # default 30; this one is honored locally
  timeline          Timeline
  transcript_id     string | null        # primary speech transcript, if any

Timeline
  tracks            Track[]              # visual z-order: index 0 is the bottom
  markers           Marker[]

Marker
  id                string
  time_seconds      number
  label             string
```

Track, clip, layer, and mixer fields are defined in [timeline-model.md](timeline-model.md), [layers.md](layers.md), and [audio-mixer.md](audio-mixer.md).

A **sequence** is a `Composition` used as the `media_id` of a clip in another composition. Nesting is specified so the model has a place for it. The MVP editor opens one composition and does not render nested sequences (see timeline-model).

## Seed a composition from the pipeline

```text
function composition_from_polish(project, asset, transcript, cues, style, enhanced | null) -> Composition:
  project.transcripts.append(transcript)
  project.media.append(asset)
  if enhanced is not null:
    project.media.append(enhanced)
  project.styles.append(style)

  video = Clip(
    kind="media_video",
    media_id=asset.id,
    start_seconds=0,
    duration_seconds=asset.duration_seconds,
    source_in=0,
    source_out=asset.duration_seconds,
    transcript_link={ transcript_id: transcript.id, word_ids: all word ids }
  )
  audio = Clip(
    kind="media_audio",
    media_id=(enhanced.id if enhanced else asset.id),
    start_seconds=0, duration_seconds=asset.duration_seconds,
    source_in=0, source_out=asset.duration_seconds,
    link_group=video.id          # trim and ignore ripple together
  )
  captions = Clip(
    kind="caption",
    start_seconds=0,
    duration_seconds=asset.duration_seconds,
    caption_style_id=style.id,
    cues=cues,
    link_group=video.id
  )
  return Composition(
    width=asset.video_width or 1920,
    height=asset.video_height or 1080,
    transcript_id=transcript.id,
    timeline=Timeline(tracks=[
      Track(kind="video", clips=[video]),
      Track(kind="audio", clips=[audio]),
      Track(kind="caption", clips=[captions])
    ])
  )
```

`link_group` is the set of clips that ripple together when a transcript ignore closes a gap. Overlay clips are not in the group unless the operator links them.

## What the MVP editor must do

- Open one composition with video, audio, and caption tracks.
- Show the transcript, strike words through, and skip them on playback ([selection-and-edits.md](selection-and-edits.md)).
- Preview the caption style on the frame ([ui-surface.md](ui-surface.md)).
- Adjust clip gain, mute, and fades ([audio-mixer.md](audio-mixer.md)).
- Export sidecars always, and a burned video when asked ([export-render.md](export-render.md)).

Shapes, blend modes other than normal, ducking, nested sequences, and NLE XML export are specified and marked later. They are not required to ship the polish pipeline.

## Persistence

JSON document `polish.project.v1` holding `Project`. Media bytes and font bytes sit beside it in a project directory, not inside the JSON. Paths in the file are relative to that directory. The directory is local. Do not put it under a path that git will pick up if it contains source media the operator has not cleared.
