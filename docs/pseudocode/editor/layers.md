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
  effects     VisualEffectNode[]  # ordered, index 0 closest to the source. Empty in the MVP. [../visual-effects-model.md](../visual-effects-model.md)
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
function draw_layer(frame, layer, source_bitmap, t, artifacts=[]):
  if layer.opacity <= 0:
    return frame
  src = apply_visual_effects(source_bitmap, layer.effects or [], artifacts, t)
  src = crop_bitmap(src, layer.crop)
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
      frame = draw_layer(frame, layer, source_at(clip, t), t, artifacts_for(clip))
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

function artifacts_for(clip) -> object:
  # Empty until a Look Good effect has run. See ../visual-effects-model.md.
  if clip.media_id is null:
    return {}
  media = project.media.by_id(clip.media_id)
  return media.artifacts or {}
```

`source_at` for video seeks to the source clock. Time spent inside earlier skip ranges is not added back: the source clock equals `source_in + (t - clip.start) * speed` only when skips have **not** been rippled closed. After a ripple ([selection-and-edits.md](selection-and-edits.md)), skip ranges are gone and the following clips have moved earlier, so the mapping stays linear inside each clip.

## MVP versus later

| Piece | When |
| --- | --- |
| `media_video`, `caption`, transform, crop, opacity, blend `normal` | MVP |
| `text` overlays that reuse `CaptionStyle` font fields | MVP, one text clip is enough |
| Image, video, and GIF overlays | In scope with the editor. Placement, loop, and fades are [overlays.md](overlays.md). The polish seeder does not create them |
| `shape` | Later. The type stays; the seeder does not create shapes |
| `multiply` and `screen` | Later. Stored and painted as `normal` until a compositor implements them |
| Non-empty `effects` | Later. Look Good nodes, Eye Contact, chroma, and color. Empty list draws as before |

## Errors

| Case | Behaviour |
| --- | --- |
| Scale of 0 | Skip the layer |
| Crop that inverts (left > right or top > bottom) | Reject the edit |
| Opacity outside 0..1 | Clamp on write |
| Missing image or font | Skip the layer and add a report line. Do not fail the whole preview |
| Rotation on a caption block | Allowed. The safe-margin clamp runs before rotation, so a large rotation can leave the frame. That is the operator's choice |

## Descript menus mapped to actions (for comparison)

From the signed build (**decompiled**: chunk 8211 for the timeline context menu, the app chunk for the New layer menu and the empty-scene overlay). Item labels are Descript's UI text. The right-hand column is the Redux action each item dispatches; `analyticsCtx.context` is `timeline/context_menu` or `add_new_layer_panel`. Use these as a checklist for our own menu. Our commands do not need the same names.

### Right-click a timeline clip

| Item | Action |
| --- | --- |
| Split scene at playhead | `EDITOR/CARD ADD_CARD_BOUNDARY_AT_TIME_OFFSET` (observed as commit "split scene") |
| Add layer ▸ | Opens the New layer menu below (flag `plus-insert-button`) |
| Reorder ▸ | `REORDER_CARD_LAYERS_WITH_SOURCE_TRACK_ID` |
| Edit sequence | `SET_ACTIVE_SEQUENCE` |
| View media | `SET_SIDEBAR_STATE` (media) + `SET_ACTIVE_MEDIA_REF` |
| Split clip | `EDITOR/TIMELINE SPLIT_CLIP_AT_TIME_OFFSET` |
| Include in script | `TRANSCRIBE_AND_MOVE_PIN_TO_SCRIPT` |
| Remove from script | `MOVE_SCRIPT_TO_PIN` |
| Add gap clip | `INSERT_GAP_AT_TIME_OFFSET` (default `insertGapDuration`) |
| Edit custom animation | `SET_ACTIVE_STORYBOARD_CUE` + `SEEK_TO_TIME` |
| Add volume keyframe · Dip volume · Auto-level clip(s) | Timeline handlers not resolved |
| Add freeze frame | `ADD_FREEZE_FRAME_AT_TIME_OFFSET` |
| Convert generated speech to media | `CONVERT_AI_SPEECH_TO_NORMAL_AUDIO` |
| Detach audio | `onDetachAudio` prop; observed commit `EDITOR/MEDIA/DETACH_AUDIO_AND_VIDEO` |
| Delete | `EDITOR/TIMELINE/DELETE_TAUS` (observed, "delete clips") |

### Right-click a time range (timeline or script selection)

| Item | Action |
| --- | --- |
| Add cue for range | Storyboard cue |
| Add label for range | `ADD_TAG_IN_TIME_RANGE` |
| Replace with gap clip | `DELETE_TIME_RANGE` |
| Dip volume | Unresolved, as above |
| Restore removed media | `RESTORE_REMOVED_MEDIA` |
| Realign words in range | `REALIGN_TIME_RANGE` |
| Include in / Remove from script | As above |

### New layer menu ("+" or Add layer)

| Item | Action |
| --- | --- |
| Files | Opens the project-files pane. Double-click inserts with `EDITOR/CARD_LAYER/ADD_PIN_COMPONENT {content: {type: media}}` targeting the current scene (observed as commit "add layer") |
| Recording | `SET_WEB_RECORDER_TARGET_TYPE("card")` + `SET_TARGET_TYPE_EXPLICIT` + `TOGGLE_WEB_TIMELINE_RECORDER_TOOLBAR("camera")` |
| Captions | A live-text layer of kind Captions |
| Text | `ADD_PIN_COMPONENT` vector Text: font size 50, box 0.2 × 0.06 of the frame. Title (200, 0.6 × 0.15) and Subtitle (100, 0.35 × 0.1) presets also exist |
| Placeholder | `ADD_PIN_COMPONENT` vector `{type: placeholder, variant: "b-roll"}` |
| Live text ▸ Timer · Current marker · Current speaker · Current composition | `ADD_PIN_COMPONENT` vector live-text kinds (Current speaker = active-speaker binding) |
| Shapes ▸ | Shapes pane |
| Videos · Backgrounds · Images · Illustrations · Music · Sound effects | Cloud-library panes for `stock-footage`, `stock-backgrounds`, `stock-photos`, `stock-illustrations`, `stock-music`, `stock-sfx` ([stock-asset-providers.md](stock-asset-providers.md#how-descript-does-it-for-comparison)) |
| GIPHY GIFs · GIPHY stickers | `giphy-gifs`, `giphy-stickers` panes, only with Drive feature `gifs_and_stickers` |
| Generate image | `SET_SIDEBAR_STATE {item: Conductor}` + `SET_AI_ACTIONS_PROMPT {presetId: "generate-image", entrypoint: "selection-toolbar"}` |

The order depends on the composition: audio items come first in audio-only projects, visual items first in video projects. Pane titles group the items as Videos, GIFs, Images and Audio.

### Empty-scene overlay ("Create a scene" / "Create a layout")

| Button | Action |
| --- | --- |
| Generate visuals | `SET_SIDEBAR_STATE` Conductor + `SET_AI_ACTIONS_PROMPT {presetId: "generate-image", entrypoint: "empty_scene_overlay"}` |
| Layout / Select template | Layout picker |
| Layer / Add layer | New layer menu |
| Close | Offers "Hide until project is reopened" |

Telemetry: `empty_scene_overlay_opened`, `empty_scene_overlay_action_clicked {generate_media | add_layout | add_layer}`, `empty_scene_overlay_dismissed`.
