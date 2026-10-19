# Caption style

Local style for Polish Clips captions. The Descript OpenAPI has **no** caption-style schema (static, version 1.2, 2026-10-19). An Underlord prompt such as "add classic karaoke-style captions" is free text; the resulting look is uncontrolled (**inferred** from that absence). Style lives in this model and is applied by the preview and by [caption-burnin.md](caption-burnin.md).

Cue text still comes from [captions.md](captions.md). Ignored words never enter a `Cue`. This file does not change that.

## Types

```text
FontSource
  kind            "web_safe" | "custom"
  family          string              # CSS family name used at draw time
  font_asset_id   string | null       # set when kind is custom

FontAsset
  id              string
  filename        string              # original name, display only
  format          "ttf" | "otf" | "woff" | "woff2"
  bytes_sha256    string
  family          string              # parsed name, or the filename stem
  path            string              # project-local file

Color                         # "#RRGGBB" or "#RRGGBBAA", sRGB

CaptionStyle
  id                    string
  name                  string
  font
    source              FontSource
    weight              400 | 500 | 600 | 700 | 800
    size_px             number        # at a 1080px-tall reference frame
    letter_spacing_em   number        # default 0
  fill                  Color         # glyph fill, default #FFFFFFFF
  outline
    enabled             boolean
    color               Color
    width_px            number        # reference px, default 2
  shadow
    enabled             boolean
    color               Color
    offset_x_px         number
    offset_y_px         number
    blur_px             number
  background
    mode                "none" | "pill" | "line"
    color               Color         # default #000000B3
    padding_x_px        number
    padding_y_px        number
    radius_px           number        # pill corner radius
  align                 "left" | "center" | "right"
  position
    preset              "bottom-center" | "lower-third" | "top-center" | "middle" | "custom"
    x                   number        # 0..1 of frame width; used when preset is custom
    y                   number        # 0..1 of frame height; used when preset is custom
    safe_margin         number        # fraction of the shorter frame side, default 0.05
  max_lines             integer       # default 2; burn-in will not exceed this
  line_gap_px           number        # gap between baselines extra, default 8 at 1080
  animation
    preset              "none" | "word-highlight" | "fade"
    highlight_color     Color         # word-highlight only, default #FFE14AFF
    fade_ms             number        # fade in and out, default 160
```

`size_px`, outline width, shadow, padding, radius, and line gap are authored at a **1080px frame height**. At draw time multiply by `frame_height / 1080`. A 720px frame uses 2/3 of the authored pixel sizes.

## Web-safe families

These names need no upload. The renderer maps them to a font file it already ships, or to the platform font of that name:

```text
Arial, Helvetica, Verdana, Tahoma, Trebuchet MS,
Georgia, Times New Roman, Courier New, Impact
```

Anything else requires `FontSource.kind = "custom"` and a `FontAsset` stored on the project. Do not fetch a font URL at render time.

## Custom upload

```text
MAX_FONT_BYTES = 5_000_000

function add_font(project, filename, bytes) -> FontAsset:
  ext = lowercase extension of filename
  if ext not in {ttf, otf, woff, woff2}:
    fail "font must be ttf, otf, woff, or woff2"
  if len(bytes) == 0 or len(bytes) > MAX_FONT_BYTES:
    fail "font file empty or larger than 5 MB"
  if not looks_like_font(bytes, ext):
    fail "file is not a font container"
  family = name_table_family(bytes) or stem(filename)
  asset = FontAsset(
    id=new_id(), filename, format=ext,
    bytes_sha256=sha256(bytes), family=family,
    path=write_project_file(project, "fonts/" + id + "." + ext, bytes)
  )
  project.fonts.append(asset)
  return asset
```

`looks_like_font` checks magic bytes only (`OTTO`, `wOFF`, `wOF2`, or a TrueType `00 01 00 00` / `true`). It does not execute the font. A broken name table falls back to the filename stem.

## Presets

`preset_style(name)` returns a full `CaptionStyle`. Operators edit a copy; presets stay immutable.

| Preset | position.preset | background | animation | Notes |
| --- | --- | --- | --- | --- |
| `bottom-center` | bottom-center | pill | none | Default. White fill, black outline, dark pill |
| `lower-third` | lower-third | line | none | Sits above the bottom safe area, left-aligned within the centered block |
| `top-center` | top-center | pill | none | Same colors as bottom-center |
| `karaoke` | bottom-center | none | word-highlight | Outline on, pill off, highlight color on the active word |
| `fade-bottom` | bottom-center | pill | fade | `fade_ms` 160 |

Anchor implied by the preset (the custom preset uses `position.x` / `position.y` as the anchor point):

```text
bottom-center   anchor = bottom-center    y = 1 - safe_margin
lower-third     anchor = bottom-center    y = 0.78
top-center      anchor = top-center       y = safe_margin
middle          anchor = center           y = 0.50
custom          anchor = center           x, y from the style
```

`lower-third` uses `align = left` and a block whose width is 80% of the frame, centered horizontally. The other stock presets use `align = center` and a block width of 90% of the frame.

## Layout box

```text
function caption_box(style, frame_w, frame_h) -> Rect:
  s = frame_h / 1080
  margin = style.position.safe_margin * min(frame_w, frame_h)
  block_w = frame_w * (0.80 if style.position.preset == "lower-third" else 0.90)
  block_h = (style.font.size_px * s + style.line_gap_px * s) * style.max_lines
  (ax, ay) = anchor_point(style, frame_w, frame_h)
  # Place the block so the anchor sits on the preset point, then clamp
  # the rectangle inside [margin, margin, frame_w - margin, frame_h - margin].
  rect = place(anchor, ax, ay, block_w, block_h)
  return clamp_inside(rect, margin, frame_w, frame_h)
```

If the clamped box is shorter than one line, shrink `size_px` in the draw call (not in the saved style) down to a floor of 18 reference pixels. If the text still overflows `max_lines`, ellipsize the last visible line. The saved style stays what the operator set.

## Word spans

Karaoke needs per-word times. [captions.md](captions.md) stores them on the cue:

```text
CueWord
  word_id         string
  text            string
  start_seconds   number
  end_seconds     number
```

`animation.preset == "word-highlight"` requires every cue to have `words`. A cue with an empty `words` list falls back to `none` for that cue and records the fallback. Ignored words are already absent from `Cue.words`.

## Errors

| Case | Behaviour |
| --- | --- |
| Unknown web-safe family | Reject the style on save |
| Custom font id missing from the project | Reject on save. Render must not substitute a silent default |
| `size_px` < 8 or > 200 | Reject on save |
| `safe_margin` not in 0..0.2 | Reject on save |
| `max_lines` not in 1..4 | Reject on save |
| `fade_ms` < 0 or > 2000 | Reject on save |
| Color not `#RRGGBB` or `#RRGGBBAA` | Reject on save |

No HTTP 402. Style is local.

## Build options

| Option | Notes |
| --- | --- |
| This model + canvas preview | Required for the editor. Preview code is in [editor/ui-surface.md](editor/ui-surface.md) |
| ASS export of the same model | [caption-burnin.md](caption-burnin.md). Preferred file burn-in |
| Underlord "add captions" | Does not read `CaptionStyle`. Leave it for the black-box backend only |
