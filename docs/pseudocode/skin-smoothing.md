# Skin smoothing

Local, optional appearance soften on a face region. Descript’s product behaviour is summarized in [../descript-analysis/skin-smoothing.md](../descript-analysis/skin-smoothing.md). This file is our own pipeline. It is **later** than the polish-clip MVP. Eye Contact is not this effect and stays a research note.

## Input / output

```text
input:
  clip             Clip             # video
  options
    strength       "low" | "medium" | "high"
    regions        "face" | "skin_only"     # skin_only tries to keep eyes and mouth sharper
output:
  asset            MediaAsset       # new video; source kept
  report
    frames         integer
    faces_skipped  integer
```

## Algorithm

```text
function smooth_skin(clip, options) -> (asset, report):
  skipped = 0
  frames = []
  for frame in decode(clip):
    boxes = face_boxes(frame)            # open detector, one or two faces
    if boxes is empty or len(boxes) >= 3:
      frames.append(frame)
      skipped += 1
      continue
    out = frame
    for box in boxes:
      mask = skin_mask(frame, box, options.regions)
      radius = { low: 2, medium: 4, high: 8 }[options.strength]
      blurred = bilateral_or_guided(frame, radius)
      out = composite(out, blurred, mask)
    frames.append(out)
  return encode(frames, copy_audio(clip)), report(len(frames), skipped)
```

`skin_mask` is an ellipse on the face box, feathered. `skin_only` punches out smaller ellipses over the eyes and mouth so they stay sharp. No identity embedding is computed or stored. Boxes are discarded after the frame.

If the face is under about 64 px on the long side, skip that box and count it in `faces_skipped`. Low light is not detected specially; a missed box is a skip.

## Build options

| Path | Notes |
| --- | --- |
| Local detector + edge-preserving blur | Default for this spec. Runs on device. No credits |
| Underlord prompt “apply skin smoothing” | Unverified. No schema field (static). Do not block on it |
| Descript Eye Contact | Different effect. Out of this file |

## Errors

| Case | Behaviour |
| --- | --- |
| No video | Fail |
| Detector missing | Fail the stage. Do not upload frames anywhere to compensate |
| Every frame skipped | Return the original and say no face was found |

No 402.
