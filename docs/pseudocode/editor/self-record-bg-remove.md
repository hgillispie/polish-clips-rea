# Self-record with background removal

Capture the operator's camera (and optional mic) while the composition preview plays, remove the background, and place the result as an overlay on the original timeline. The original camera clip stays. This is a picture-in-picture or a full-frame layer, not a destructive replace.

Green Screen on imported footage is `com.descript.backgroundRemoval` and the cloud task `background_removal` → artifact `background_mask` ([../green-screen.md](../green-screen.md)). Chroma key is the local color key ([../chroma-key.md](../chroma-key.md)). This file is the capture path. It writes a `BackgroundMask` the same shader reads. It does not POST `background_removal` during the take. Portrait Lighting, Uplighting, and Blur speaker background can use that mask afterwards without a second matte format.

## Input / output

```text
input:
  composition          Composition
  options
    camera_device_id   string | null
    include_mic        boolean         # default false; voice stays on voiceover.md if they want a separate track
    mode               "segmentation" | "chroma"
    chroma_color       Color           # default #00FF00, used when mode is chroma
    chroma_threshold   number          # 0..1, default 0.35
    placement          "pip" | "full_frame"
    pip_corner         "top-left" | "top-right" | "bottom-left" | "bottom-right"
output:
  asset                MediaAsset      # video with straight alpha, or a color clip plus a matte
  overlay              OverlayClip
```

## Capture

```text
function self_record(composition, options) -> output:
  constraints = { video: camera_constraints(options.camera_device_id), audio: options.include_mic }
  stream = getUserMedia(constraints)
  preview_play(composition)                    # operator sees the timeline while recording
  t0 = composition.playhead
  frames = []
  audio = []
  until the operator stops:
    bitmap = grab_video_frame(stream)
    mask = matte(bitmap, options)              # below
    frames.append(apply_matte(bitmap, mask))
    if options.include_mic:
      audio.append(grab_audio(stream))
  asset = encode_with_alpha(frames, audio, fps=30)
  asset.local_mask = BackgroundMask(
    source = "chroma_fallback" if options.mode == "chroma" else "local_segmenter"
  )
  overlay = add_overlay(composition, asset, t0, duration(frames))
  if options.placement == "pip":
    pip_preset(overlay.clip, options.pip_corner)
  else:
    full_frame(overlay.clip)
  return asset, overlay
```

`encode_with_alpha` prefers a codec that stores straight alpha (WebM VP9 with alpha in the browser, or a ProRes 4444 / qtrle file on desktop). If the encoder cannot store alpha, write the color video and a sibling grayscale matte, and teach `overlay_bitmap` to multiply them. The timeline still has one overlay clip; the matte is an asset sidecar.

The mic, when included, is the audio of this overlay clip. It does not punch into the dialogue track. Headphones are assumed so the preview does not feed back.

## Segmentation

Default mode. A selfie-segmentation class model (MediaPipe selfie segmentation or a similar person-segmenter) runs per frame. WebGPU when the page has it, otherwise WASM or WebGL. The model file is an open checkpoint the implementation chooses; this spec does not vendor weights.

```text
function matte_segmentation(bitmap) -> mask:
  # BackgroundMask channels the green-screen shader multiplies: r * a, 1 = keep.
  raw = segmenter.infer(bitmap)              # person probability
  raw = temporal_smooth(raw, previous_mask, alpha=0.6)
  raw = refine_edges(raw, feather_px=2)
  return { r: raw, a: raw, source: "local_segmenter" }

function apply_matte(bitmap, mask) -> bitmap:
  out = bitmap with alpha
  keep = mask.r if mask has channel r else mask
  out.alpha = keep
  return out
```

`temporal_smooth` mixes the previous mask so the edge does not flicker. The first frame uses the raw mask.

If the segmenter fails to load, switch this session to chroma mode and say so. Do not block the recording behind a download once the operator has started; the fallback is chosen before `getUserMedia` if the model is missing.

## Chroma key fallback

```text
function matte_chroma(bitmap, key_color, threshold) -> mask:
  for pixel in bitmap:
    dist = color_distance(pixel.rgb, key_color) / max_distance
    # 0 = exact key (drop), 1 = far from key (keep)
    mask = clamp((dist - threshold) / 0.15, 0, 1)
  mask = feather(mask, 1px)
  return { r: mask, a: mask, source: "chroma_fallback" }
```

Use this when the operator has a green or blue backdrop. It is also the fallback when segmentation is unavailable. Spill suppression (reducing green in the kept pixels) is a one-line despill toward neutral on pixels whose mask is between 0 and 1. Skip despill in segmentation mode.

## Composite

The overlay track index is above the original video track, so the keyed shot paints on top. The original clip is not muted and not trimmed. Caption burn-in still paints above both when enabled.

A full-frame placement covers the original. The operator can lower opacity or scale it back to picture-in-picture without re-recording, because the alpha is in the asset.

## Errors

| Case | Behaviour |
| --- | --- |
| Camera permission denied | Fail before record |
| Segmentation model missing | Fall back to chroma and record the fallback |
| Frame size changes mid-record | Stop and keep the frames already accepted |
| Alpha encode fails | Write color + matte sidecar. Fail only if both writes fail |
| Preview playback underrun | Keep recording. The playhead time at start is what syncs the overlay |

No 402 on the capture itself. The stored mask is `source: "local_segmenter"`. Enabling Green Screen, blur, portrait, or uplight later calls `ensure_background_mask`, which reuses this mask and does not POST ([../green-screen.md](../green-screen.md)). Imported footage that has no local mask takes the cloud path and can spend the green-screen credit there.

## Build options

| Path | When |
| --- | --- |
| MediaPipe-class segmentation | Default. On-device, no account. Fills `BackgroundMask` |
| Another open person-segmenter on WebGPU | Swap the `segmenter` object. Same matte contract |
| Chroma key | Fallback and for a real colored backdrop. Shader in [../chroma-key.md](../chroma-key.md) |
| `POST /projects/{id}/background_removal` | Imported footage only, via [../green-screen.md](../green-screen.md). Not this capture |
