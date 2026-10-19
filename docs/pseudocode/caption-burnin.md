# Caption burn-in

Draw cue text into video frames. Sidecar SRT and VTT from [captions.md](captions.md) stay the default deliverable. Burn-in is an optional export step. Style comes only from [caption-style.md](caption-style.md).

The Descript API cannot express this. There is no caption-style field (static). Underlord may burn its own captions into a project; that look is uncontrolled (**inferred**). Polish Clips owns style on the local render.

## Input / output

```text
input:
  video            MediaAsset       # has_video = true; audio is copied through
  cues             Cue[]            # already exclude ignored words
  style            CaptionStyle
  fonts            FontAsset[]      # project fonts; empty if the style is web-safe
  options
    renderer       "auto" | "ass" | "drawtext" | "canvas"
    width          integer | null   # null = source width
    height         integer | null
    crf            integer          # default 20, libx264
output:
  video            MediaAsset       # new file; source is unchanged
  report
    renderer       string           # the one that actually ran
    cue_count      integer
    fallbacks      string[]         # e.g. "cue 4 word-highlight missing words"
```

Honor `ignored` the same way as cue building: do not read the transcript again, and do not paint `Cue.words` that are absent. If a caller passes a hand-built cue whose `words` include a word id flagged `ignored` on the transcript, drop that word and rebuild the line from the remaining words. If nothing remains, skip the cue.

## Renderer choice

```text
function burn_captions(video, cues, style, fonts, options) -> (video, report):
  if not video.has_video:
    fail "burn-in needs a video stream"
  cues = drop_ignored_word_ids(cues)          # defense in depth
  if cues is empty:
    return copy of video, report(renderer="none", cue_count=0, fallbacks=["no cues"])

  choice = options.renderer
  if choice == "auto":
    if style.animation.preset == "word-highlight":
      choice = "ass"                           # \k tags; canvas if ass fails
    else:
      choice = "ass"

  fallbacks = []
  try:
    if choice == "ass":
      out = burn_ass(video, cues, style, fonts, options, fallbacks)
    else if choice == "drawtext":
      out = burn_drawtext(video, cues, style, fonts, options, fallbacks)
    else if choice == "canvas":
      out = burn_canvas(video, cues, style, options, fallbacks)
    else:
      fail "unknown renderer"
  catch RenderError as err:
    if options.renderer == "auto" and choice != "drawtext":
      fallbacks.append(err.message)
      out = burn_drawtext(video, cues, style, fonts, options, fallbacks)
      choice = "drawtext"
    else:
      fail err

  return out, report(renderer=choice, cue_count=len(cues), fallbacks=fallbacks)
```

`auto` prefers ASS because one subtitle file carries font, outline, shadow, alignment, fade, and karaoke. `drawtext` is the fallback that needs no subtitle parser. Canvas+WebCodecs is the path that matches the on-screen preview pixel for pixel, at the cost of a full re-encode in the page.

## ASS + `ass` filter

```text
function burn_ass(video, cues, style, fonts, options, fallbacks) -> MediaAsset:
  (w, h) = output_size(video, options)
  body = ass_document(cues, style, w, h, fallbacks)
  ass_path = write_temp(body)
  font_dir = directory of fonts used by style (empty dir if web-safe)
  vf = "ass=" + escape_filter_path(ass_path) + ":fontsdir=" + escape_filter_path(font_dir)
  return ffmpeg_encode(video, vf, options, w, h)

function ass_document(cues, style, w, h, fallbacks) -> string:
  scale = h / 1080
  # PlayRes matches the output frame so margins are pixels.
  header = [
    "[Script Info]",
    "ScriptType: v4.00+",
    "PlayResX: " + w,
    "PlayResY: " + h,
    "WrapStyle: 0",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    style_line(style, scale),
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
  ]
  events = []
  for cue in cues:
    text = ass_text(cue, style, fallbacks)
    events.append("Dialogue: 0," + ass_time(cue.start_seconds) + ","
      + ass_time(cue.end_seconds) + ",Polish,,0,0,0,," + text)
  return join(header + events, "\n")
```

Mapping (reference pixels scaled by `h/1080`):

| CaptionStyle | ASS |
| --- | --- |
| `font.family` | Style `Fontname`. Custom fonts also need `fontsdir` |
| `font.weight` >= 600 | Bold -1 |
| `font.size_px` | Fontsize |
| `fill` | PrimaryColour, ASS `&HAABBGGRR` |
| `animation.highlight_color` | SecondaryColour (karaoke fill) |
| `outline.color` / `width_px` | OutlineColour / Outline. Width 0 when outline disabled |
| `shadow` | Shadow distance is `max(abs(offset_x), abs(offset_y))`. Blur is `\blur` on the event when `blur_px` > 0 |
| `background.mode = pill` or `line` | BorderStyle 3 (opaque box) and BackColour. `none` uses BorderStyle 1 |
| `align` + vertical preset | Alignment numpad: bottom-center 2, top-center 8, middle-center 5. Left variants use 1, 7, 4 |
| `safe_margin` | MarginL, MarginR, MarginV in pixels |
| `fade` | Event override `{\fad(fade_ms,fade_ms)}` |
| `word-highlight` | Karaoke `{\k<cs>}` per word, centiseconds = round(duration * 100) |

```text
function ass_text(cue, style, fallbacks) -> string:
  if style.animation.preset == "word-highlight":
    if cue.words is empty:
      fallbacks.append("cue " + cue.index + " missing words; animation none")
      return escape_ass(cue.text)
    parts = []
    for word in cue.words:
      cs = max(1, round((word.end_seconds - word.start_seconds) * 100))
      parts.append("{\\k" + cs + "}" + escape_ass(word.text))
    return " ".join(parts) if the cue text used spaces else join with the same separators as cue.text
  if style.animation.preset == "fade":
    return "{\\fad(" + style.animation.fade_ms + "," + style.animation.fade_ms + ")}" + escape_ass(cue.text)
  return escape_ass(cue.text)
```

`escape_ass` replaces `{` `\n` and `\` so cue text cannot inject override tags.

Line gap and `max_lines` are applied before the event is written: wrap `cue.text` to the caption box width using the scaled font size, keep at most `max_lines`, ellipsize the last line, join wrapped lines with `\N`.

## ffmpeg `drawtext`

Use this when ASS is unavailable, or as the `auto` fallback. One `drawtext` per wrapped line, enabled for the cue interval.

```text
function burn_drawtext(...) -> MediaAsset:
  if style.animation.preset == "word-highlight":
    fallbacks.append("drawtext has no karaoke; painting the full line")
  filters = []
  for cue in cues:
    lines = wrap(cue.text, style, frame)
    for i, line in enumerate(lines):
      (x, y) = line_origin(style, frame, i, len(lines))
      filters.append(
        "drawtext=fontfile='" + fontfile(style) + "'"
        + ":text='" + escape_drawtext(line) + "'"
        + ":fontsize=" + scaled(style.font.size_px)
        + ":fontcolor=" + style.fill
        + ":x=" + x + ":y=" + y
        + border_and_shadow(style)
        + ":enable='between(t," + cue.start_seconds + "," + cue.end_seconds + ")'"
      )
  return ffmpeg_encode(video, ",".join(filters), options, w, h)
```

Limits to record in `fallbacks` rather than pretending parity:

- No pill radius. A box is `box=1:boxcolor=...:boxborderw=...` when `background.mode` is not `none`.
- No per-word highlight.
- Fade is omitted on this path (drawtext alpha expressions are easy to get wrong across cues). Record `fade omitted`.
- `fontfile` must be a local file. Web-safe families resolve through the shipped font map. A missing file fails the stage.

## Canvas + WebCodecs

```text
function burn_canvas(video, cues, style, options, fallbacks) -> MediaAsset:
  decoder = VideoDecoder(video)
  encoder = VideoEncoder(codec="avc1", width, height, bitrate_from_crf_approx)
  # Audio is remuxed from the source, not re-synthesized, unless the
  # caller already replaced the audio with an enhanced wav.
  for frame in decoder:
    t = frame.timestamp_seconds
    bitmap = frame_to_canvas(frame)
    for cue in cues_at(cues, t):
      paint_cue(bitmap, cue, style, t)     # same box, wrap, and highlight as the preview
    encoder.encode(bitmap, t)
  return mux(encoder.output, video.audio)
```

`paint_cue` at time `t`:

- Draw the background pill or line behind the wrapped text.
- Draw each word. If `word-highlight` and `word.start_seconds <= t < word.end_seconds`, use `highlight_color` for that word and `fill` for the others.
- If `fade`, multiply alpha by the ramp: 0 at `start`, 1 after `fade_ms`, 1 until `end - fade_ms`, 0 at `end`.

This is the renderer the preview already uses ([editor/ui-surface.md](editor/ui-surface.md)). Choose it when the export must match the preview, including custom font shaping. It always re-encodes video.

## Encode

```text
function ffmpeg_encode(video, vf, options, w, h) -> MediaAsset:
  args = [
    "-i", video.path,
    "-vf", vf + ",scale=" + w + ":" + h,
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", options.crf,
    "-c:a", "copy",
    "-movflags", "+faststart",
    out_path
  ]
  run ffmpeg
  if exit != 0:
    fail RenderError(stderr tail)
  return probe(out_path)
```

Audio copy keeps the enhanced track if the input file already has it. Do not run Studio Sound inside burn-in.

## Errors

| Case | Behaviour |
| --- | --- |
| No video stream | Fail before ffmpeg |
| Empty cue list | Return the input video unchanged and say so in the report |
| Font file missing | Fail the ASS/drawtext attempt. `auto` may fall back once |
| ffmpeg non-zero | `RenderError`. `auto` falls back from ASS to drawtext once, then fails |
| WebCodecs unsupported | Fail that renderer. Do not silently switch unless `renderer` is `auto`, in which case try ASS next |
| Cue longer than the video | Clamp `end_seconds` to the video duration and record a fallback |

No 402.

## Build options

| Renderer | When |
| --- | --- |
| ASS + `ass` filter | Default export. Outline, shadow, alignment, fade, karaoke |
| `drawtext` | Fallback and simple static lines |
| Canvas + WebCodecs | Preview parity, custom shaping, word highlight when ASS karaoke is not acceptable |

Sidecar SRT/VTT is still written beside the burned file. Players that offer their own captions can ignore the burned pixels.
