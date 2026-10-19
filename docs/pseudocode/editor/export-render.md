# Export render

Offline render of one composition. Preview uses the same composite and mix functions on a short interval around the playhead. This file is the full-length path.

## Input / output

```text
input:
  project          Project
  composition_id   string
  options
    preset         "1080p" | "720p" | "source" | "audio"
    burn_captions  boolean          # default false
    sidecars       boolean          # default true
    crf            integer          # default 20
output:
  video            MediaAsset | null
  audio            MediaAsset | null
  srt              string | null
  vtt              string | null
  report
    limited        boolean
    caption_renderer string | null
    warnings       string[]
```

## Presets

| Preset | Video | Audio | Frame |
| --- | --- | --- | --- |
| `1080p` | libx264, yuv420p, crf from options | aac 192 kbps stereo | 1920×1080, composition fps |
| `720p` | same | same | 1280×720 |
| `source` | same | same | composition width and height |
| `audio` | none | aac 192 kbps, or wav if the caller asks | n/a |

Fit `source` frames inside the preset box with the composition's aspect ratio, padding black. Do not crop to fill.

## Graph

```text
function export_composition(project, composition_id, options) -> output:
  comp = project.compositions.by_id(composition_id)
  warnings = []
  duration = composition_duration(comp)
  if duration <= 0:
    fail "composition has no duration"

  (w, h) = preset_size(comp, options.preset)

  if options.preset != "audio":
    frames = []
    t = 0
    while t < duration:
      frames.append(composite_frame(comp, t, captions_visible=false))   # layers.md
      t += 1 / comp.fps
    silent_video = encode_frames(frames, w, h, comp.fps, options.crf)
  else:
    silent_video = null

  pcm, limited = mix_all(comp, duration)         # audio-mixer.md
  if limited:
    warnings.append("master limited to -1 dBFS")
  audio_file = encode_audio(pcm)

  if options.preset == "audio":
    video_out = null
    audio_out = audio_file
  else:
    video_out = mux(silent_video, audio_file)
    audio_out = null

  cues = caption_cues(comp)                      # from the caption track, else build
  srt, vtt = (null, null)
  if options.sidecars and cues is not empty:
    srt, vtt, _ = format from cues               # captions.md format_srt / format_vtt

  if options.burn_captions and video_out is not null:
    style = style of the caption clip, or preset "bottom-center"
    video_out, burn_report = burn_captions(      # caption-burnin.md
      video_out, cues, style, project.fonts, { renderer: "auto", crf: options.crf }
    )
    warnings.extend(burn_report.fallbacks)
    renderer = burn_report.renderer
  else:
    renderer = null

  return { video_out, audio_out, srt, vtt,
           report(limited, renderer, warnings) }
```

`composite_frame` already paints caption glyphs when the preview wants them. For file export, paint captions in `composite_frame` **only** when `burn_captions` is true, so a non-burned master stays clean and the sidecar carries the text. Implementation: pass `captions_visible = options.burn_captions` into the compositor, and also pass it true for the on-screen preview regardless of the export flag.

When burn-in runs as a second ffmpeg pass (`burn_captions` on an already muxed file), do not also paint captions into `frames`, or the text will be drawn twice. Preferred order:

```text
captions_visible = false during encode_frames
mux video + audio
if burn_captions:
  video_out = burn_captions(video_out, ...)
```

The preview path is the exception: it paints captions in the canvas and does not call `burn_captions`.

## Audio interval

`mix_all` calls `mix_interval` in blocks of one second, concatenates, then runs the limiter once on the master if any sample exceeds -0.1 dBFS. Ducking stays bypassed (audio-mixer). Peak EQ stays bypassed. Highpass, lowpass, fades, gain, pan, mute, and solo run.

## Errors

| Case | Behaviour |
| --- | --- |
| No clips | Fail |
| Decoder error on one clip | Fail the export with the clip id. Preview may skip that frame and show a held last frame |
| Burn-in `RenderError` after a successful mux | Keep the unburned mux, set the stage report to failed, still write sidecars |
| Sidecar with zero cues | Write no files, warning "no captions" |
| Disk full | Fail and delete the partial output |

No 402. A Descript `POST /jobs/publish` is a different export, specified in [../polish-pipeline.md](../polish-pipeline.md), and it does not take `CaptionStyle`.

## Build options

| Path | When |
| --- | --- |
| This graph | Local editor export. Required once the editor ships |
| Pipeline `clip-cut` concat | Still valid for a one-file polish with no overlays. It does not composite layers |
| Descript publish | Black-box backend only. Uncontrolled caption style |
