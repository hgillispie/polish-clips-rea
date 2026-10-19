# Object removal

Mask a region and fill it from surrounding pixels. Descript’s documented version is **Edit with AI** on **still images**, not on video ([../descript-analysis/object-removal.md](../descript-analysis/object-removal.md)). This spec covers a still first and a video later. Neither is in the polish-clip MVP.

## Input / output

```text
input:
  asset            MediaAsset       # image, or video when options.video is true
  mask             Mask             # 0..1, same width and height as the frame; 1 = remove
  options
    video          boolean          # default false
    prompt         string | null    # optional text for a generative fill; null = classical inpaint
output:
  asset            MediaAsset       # new file; source kept
  report
    method         "classical" | "generative"
    frames         integer

Mask
  width, height    integer
  values           float[]          # row-major, or a grayscale PNG in the project
```

The mask is drawn by the operator. We do not infer an object from a text prompt in the classical path.

## Still image

```text
function remove_object(asset, mask, options) -> (asset, report):
  if asset.kind != "image" and not options.video:
    fail "video removal is off"
  if options.prompt is null or options.prompt.trim() == "":
    out = inpaint_classical(decode(asset), mask)
    return write(out), report("classical", 1)
  out = inpaint_generative(decode(asset), mask, options.prompt)
  return write(out), report("generative", 1)

function inpaint_classical(image, mask) -> image:
  # Telea or Navier-Stokes style fill, radius about 5 px, iterated while the
  # hole shrinks. OpenCV's inpaint is one implementation; a small pure
  # implementation is fine. No Descript weights.
  return inpaint(image, mask > 0.5)
```

Generative fill is optional and calls a model the operator configured. If none is configured, fail that branch and offer the classical path. Do not send the image to Descript.

## Video (later)

```text
function remove_object_video(asset, masks_by_time, options) -> asset:
  if not options.video:
    fail "video removal is off"
  frames = []
  for frame, t in decode_video(asset):
    mask = mask_at(masks_by_time, t) or propagate(previous_mask, frame)
    frames.append(inpaint_classical(frame, mask))
  return encode(frames, copy_audio(asset))
```

`propagate` is a stub: hold the last mask. Optical-flow propagation is a later upgrade. Flicker across frames is an accepted limitation until then.

Help’s image-only limit means a Descript publish or Underlord job is the wrong tool for this video path (**static** absence of a video erase feature).

## Errors

| Case | Behaviour |
| --- | --- |
| Mask size mismatch | Fail before inpaint |
| Empty mask | Return the original |
| Generative model not configured | Fail that branch only |
| Video flag false on a video | Fail with a pointer at the flag |

No 402.
