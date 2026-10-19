# Layers

Visual clips carry a `VisualLayer`. The preview and [export-render.md](export-render.md) composite these bottom to top. This is ordinary 2D compositing, not a description of Descript's renderer.

## Types

```text
VisualLayer
  kind        "media_video" | "text" | "shape" | "image" | "caption"
  transform   Transform
  crop        Crop
  opacity     number          # 0..1, default 1; multiplies transform is separate
  blend       "normal" | "multiply" | "screen"
  text        TextOverlay | null
  shape       ShapeOverlay | null
  caption_style_id  string | null

Transform
  x           number          # anchor x, 0..1 of the frame (default 0.5)
  y           number          # anchor y, 0..1 of the frame (default 0.5)
  scale_x     number          # default 1
  scale_y     number          # default 1
  rotation_deg number         # clockwise, default 0
  anchor      "center"        # MVP locks the anchor to the layer center

Crop
  left        number          # 0..1 of the source rect, default 0
  top         number
  right       number
  bottom      number

TextOverlay
  body        string
  style_id    string | null   # reuse CaptionStyle font/fill/outline; position is the transform
  align       "left" | "center" | "right"

ShapeOverlay
  shape       "rect" | "ellipse"
  fill        Color
  stroke      Color
  stroke_px   number
```

A caption clip's layer kind is `caption`. Its glyphs come from `Clip.cues` and `CaptionStyle`, not from `TextOverlay`. The burn path is [../caption-burnin.md](../caption-burnin.md). The preview uses the same layout box as [../caption-style.md](../caption-style.md).

## Draw one layer

```text
function draw_layer(frame, layer, source_bitmap, t):
  if layer.opacity <= 0:
    return frame
  src = crop_bitmap(source_bitmap, layer.crop)
  if src is empty:
    return frame
  w = src.width * layer.transform.scale_x
  h = src.height * layer.transform.scale_y
  cx = layer.transform.x * frame.width
  cy = layer.transform.y * frame.height
  sprite = rotate(scale(src, w, h), layer.transform.rotation_deg)
  if layer.blend != "normal":
    # Later. MVP treats multiply and screen as normal and records a warning once per export.
    blend = "normal"
  else:
    blend = "normal"
  return composite_over(frame, sprite, center=cx,cy, opacity=layer.opacity, blend=blend)
```

`source_bitmap` depends on kind:

| Kind | Bitmap at time t |
| --- | --- |
| `media_video` | Decoded frame at source time `source_in + (t - clip.start) * speed`, if `t` is not inside a skip range |
| `image` | The image asset, constant |
| `text` | Rasterize `TextOverlay.body` with the referenced style's font, fill, and outline |
| `shape` | Fill a rect or ellipse of the layer's laid-out size |
| `caption` | Rasterize the active cue (see below) |

Caption at time `t`:

```text
function caption_bitmap(clip, style, t, frame_w, frame_h) -> bitmap | null:
  cue = the cue on clip where cue.start <= t < cue.end, after skip ranges
  if cue is null:
    return null
  box = caption_box(style, frame_w, frame_h)
  return paint_cue(box, cue, style, t)     # same paint as caption-burnin canvas path
```

The caption layer's transform defaults to identity in the box's own coordinate system (the box already encodes position). Operator overrides on `transform` offset that box: `x`/`y` replace the preset anchor, `scale_*` scales the glyphs, `rotation_deg` rotates the block.

## Stacking a frame

```text
function composite_frame(composition, t, captions_visible) -> bitmap:
  frame = empty bitmap(composition.width, composition.height)   # transparent, then black under it
  tracks = visual tracks sorted by index ascending
  for track in tracks:
    if track.kind == "caption":
      continue                               # captions paint in a later pass
    for clip in track.clips:                 # array order; later overlaps win
      if not clip_active(clip, t):
        continue
      layer = clip.layer or default_media_layer(clip)
      frame = draw_layer(frame, layer, source_at(clip, t), t)
  if captions_visible:
    for clip in caption_track.clips:
      if clip_active(clip, t):
        style = project.styles.by_id(clip.caption_style_id)
        bitmap = caption_bitmap(clip, style, t, frame.width, frame.height)
        if bitmap is not null:
          frame = composite_over(frame, bitmap, opacity=1, blend="normal")
  return frame

function clip_active(clip, t) -> boolean:
  if t < clip.start_seconds or t >= clip.start_seconds + clip.duration_seconds:
    return false
  for skip in clip.skip_ranges:
    if skip.start_seconds <= t < skip.end_seconds:
      return false
  return true
```

`source_at` for video seeks to the source clock. Time spent inside earlier skip ranges is not added back: the source clock equals `source_in + (t - clip.start) * speed` only when skips have **not** been rippled closed. After a ripple ([selection-and-edits.md](selection-and-edits.md)), skip ranges are gone and the following clips have moved earlier, so the mapping stays linear inside each clip.

## MVP versus later

| Piece | When |
| --- | --- |
| `media_video`, `caption`, transform, crop, opacity, blend `normal` | MVP |
| `text` overlays that reuse `CaptionStyle` font fields | MVP, one text clip is enough |
| `shape` and `image` | Later. Types are stable; `place_clip` may accept them and the renderer may draw them, but the polish seeder does not create them |
| `multiply` and `screen` | Later. Stored and painted as `normal` until a compositor implements them |

## Errors

| Case | Behaviour |
| --- | --- |
| Scale of 0 | Skip the layer |
| Crop that inverts (left > right or top > bottom) | Reject the edit |
| Opacity outside 0..1 | Clamp on write |
| Missing image or font | Skip the layer and add a report line. Do not fail the whole preview |
| Rotation on a caption block | Allowed. The safe-margin clamp runs before rotation, so a large rotation can leave the frame. That is the operator's choice |
