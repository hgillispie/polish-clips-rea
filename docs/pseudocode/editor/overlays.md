# Overlays

An overlay is a visual clip on a track with `kind = "overlay"`. It paints above the base video track (higher `Track.index`). Stills, looping video, and animated GIFs share one placement model. Stock search is [stock-asset-providers.md](stock-asset-providers.md). A webcam with the background removed is [self-record-bg-remove.md](self-record-bg-remove.md) and lands here as an overlay with an alpha channel.

Shapes stay a later layer kind ([layers.md](layers.md)). This file makes **image, video, and GIF** overlays part of the editor, which the polish seeder does not create by itself.

## Types

```text
OverlaySource
  kind            "image" | "video" | "gif"
  media_id        string
  loop            boolean         # video and gif; ignored for a still
  alpha           "none" | "straight"   # straight alpha when the file has it

OverlayTiming
  fade_in_seconds number          # default 0; opacity ramp, not an audio fade
  fade_out_seconds number         # default 0

OverlayClip
  clip            Clip            # kind "image" or "media_video"; gif uses "image" frames
  source          OverlaySource
  timing          OverlayTiming
  attribution     Attribution | null
```

`Clip.layer` is a `VisualLayer` with kind `image` or `media_video`. Transform, crop, opacity, and rotation are the fields in [layers.md](layers.md). Blend stays `normal` until multiply/screen ship.

## Place

```text
function add_overlay(composition, asset, at, duration | null) -> OverlayClip:
  track = topmost Track(kind="overlay") or new Track(kind="overlay", name="Overlay")
  # New overlay tracks get index = max(existing visual index) + 1
  # so they paint above the base video. Caption tracks still paint last
  # when captions_visible is true (layers.md).
  kind = "image" if asset is still or gif else "media_video"
  dur = duration if duration is not null else default_duration(asset)
  clip = Clip(
    kind=kind,
    media_id=asset.id,
    start_seconds=at,
    duration_seconds=dur,
    source_in=0,
    source_out=min(asset.duration_seconds or dur, dur),
    layer=VisualLayer(
      kind=kind,
      transform=Transform(x=0.5, y=0.5, scale_x=1, scale_y=1, rotation_deg=0),
      opacity=1,
      crop=Crop(0, 0, 0, 0),
      blend="normal"
    )
  )
  source = source_of(asset)
  source.loop = asset.kind == "gif" or (asset.kind == "video" and asset.duration_seconds < dur)
  place_clip(track, clip)
  return OverlayClip(clip, source, OverlayTiming(0, 0), asset.attribution)

function default_duration(asset) -> number:
  if asset.kind == "image":
    return 5
  return asset.duration_seconds
```

Timing in and out is `start_seconds` and `duration_seconds`. Dragging the clip body moves it. Dragging an edge trims it and, for video, moves `source_out` / `source_in` the same way as [selection-and-edits.md](selection-and-edits.md). A still has no source clock; trimming only changes how long it shows.

## Draw

```text
function overlay_bitmap(overlay, t) -> bitmap:
  clip = overlay.clip
  local = t - clip.start_seconds
  authored = clip.layer.opacity
  if overlay.timing.fade_in_seconds > 0 or overlay.timing.fade_out_seconds > 0:
    clip.layer.opacity = authored * fade_env(local, overlay.timing)
  if overlay.source.kind == "image" and not overlay.source.loop:
    bitmap = decode_image(clip.media_id)
  else if overlay.source.kind == "gif" or overlay.source.loop:
    frames = decode_frames(clip.media_id)       # each frame has its own delay
    bitmap = frame_at_loop(frames, local)
  else:
    src_t = clip.source_in + local * clip.speed
    bitmap = decode_video_frame(clip.media_id, src_t)
  clip.layer.opacity = authored
  return bitmap
```

`frame_at_loop` walks frame delays and wraps with modulo the total GIF or video duration. GIF disposal and frame alpha are honored when the decoder provides them. A GIF without per-frame alpha is opaque.

`composite_frame` already walks overlay tracks above video tracks. Pass the bitmap from `overlay_bitmap` into `draw_layer`. Opacity fades multiply the layer opacity for that frame only; the saved `layer.opacity` stays the authored value.

Picture-in-picture is a preset, not a new type:

```text
function pip_preset(clip, corner) -> void:
  # corner: top-left, top-right, bottom-left, bottom-right
  clip.layer.transform.scale_x = 0.28
  clip.layer.transform.scale_y = 0.28
  clip.layer.transform.x = 0.08 or 0.92
  clip.layer.transform.y = 0.12 or 0.88
```

Full-frame is scale 1 at (0.5, 0.5).

## Cache

Downloaded and imported bytes live in the project media directory. The `MediaAsset` records `origin: "import" | "stock" | "record"` and, for stock, the `Attribution` from the provider. Re-adding the same provider asset id reuses the file.

## Errors

| Case | Behaviour |
| --- | --- |
| Unsupported container | Fail the import. Do not place an empty clip |
| GIF decode error | Fail that asset. Leave the timeline unchanged |
| Zero duration after trim | Reject the trim |
| Overlay track missing at render | Skip. Base video still exports |
| Alpha on a codec the encoder cannot carry | Flatten against transparent, then composite in `composite_frame` before encode. The export file is opaque |

No 402.
