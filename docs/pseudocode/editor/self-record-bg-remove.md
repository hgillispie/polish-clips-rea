# Self-record with background removal

Capture the operator's camera (and optional mic) while the composition preview plays, remove the background, and place the result as an overlay on the original timeline. The original camera clip stays. This is a picture-in-picture or a full-frame layer, not a destructive replace.

Descript's help describes a **Green Screen** effect that removes a background with no physical screen, and a separate **Chroma Key** effect that is better when a real green screen is present (static, help center, fetched 2026-10-19). Those are their product features. This spec is a local capture pipeline. It does not call their effect.

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
  # mask: float 0..1 per pixel, 1 = keep (person)
  raw = segmenter.infer(bitmap)              # person probability
  raw = temporal_smooth(raw, previous_mask, alpha=0.6)
  return refine_edges(raw, feather_px=2)

function apply_matte(bitmap, mask) -> bitmap:
  out = bitmap with alpha
  out.alpha = mask
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
  return feather(mask, 1px)
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

No 402. No Descript Green Screen job.

## Build options

| Path | When |
| --- | --- |
| MediaPipe-class segmentation | Default. On-device, no account |
| Another open person-segmenter on WebGPU | Swap the `segmenter` object. Same matte contract |
| Chroma key | Fallback and for a real colored backdrop |
| Descript Green Screen via an Underlord prompt | Unverified. The OpenAPI has no green-screen field (static). Do not block this feature on that prompt |
