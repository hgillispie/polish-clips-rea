# Skin smoothing

Local face soften. Flag `beautifyRequested`. First apply on a file costs **5 AI credits**. Not Eye Contact, and not a `com.descript.*` HD id.

Analysis: [../descript-analysis/skin-smoothing.md](../descript-analysis/skin-smoothing.md). Node list: [visual-effects-model.md](visual-effects-model.md).

The public client does not POST `background_removal` or `eye_gaze_correction` for this effect. No endpoint was recovered. The work runs when the flag is set, and the credit sentence is on the agent field.

## Parameter vector (decompiled module 351916)

Default `[0.4, 3, 0.0212, Regions, 1, 0.3, 0.3, 2.5]`.

The pack audit calls the module's minified index symbols `EX` and `y0`. The module is not in git. Use these indexes:

| Index | Field | Default |
| --- | --- | --- |
| 0 | base_strength | `0.4` |
| 1 | radius | `3` |
| 2 | edge_feather | `0.0212` |
| 3 | mask_area | `REGIONS` or `WHOLE_FACE` |
| 4 | forehead | `1` |
| 5 | cheeks | `0.3` |
| 6 | laugh_lines | `0.3` |
| 7 | under_eyes | `2.5` |

`mask_area` is stored as an enum, not a float. `REGIONS` is the default. Agent field `skinSmoothing` is boolean only: `true` means this vector, `false` disables. The agent cannot set radius.

Edge feather's unit is unlabeled. Apply it as a fraction of the face-box min side (**inferred**).

## Types

```text
SkinSmoothNode
  type        "skin_smoothing"       # not an HD wire string; minified binding mo.WaC
  enabled     boolean
  params      as the table

SkinCredit
  file_id     string
  charged     boolean                # true after the first successful enable
```

Credit key `skin_smoothing` → `ai_effects`.

## Enable

```text
function enable_skin_smoothing(layer, media, params | null) -> void:
  vector = params or default_vector()
  check_vector(vector)
  if not credit_for(media.id).charged:
    # 5 AI credits per file the first time (static-bundle).
    charge(category="ai_effects", key="skin_smoothing", amount=5, file=media.id)
    credit_for(media.id).charged = true
  push node(type="skin_smoothing", enabled=true, params=vector)
  media.beautifyRequested = true

function check_vector(v) -> void:
  if v.mask_area not in ("REGIONS", "WHOLE_FACE"):
    fail "mask area"
  if v.base_strength < 0 or v.base_strength > 1:
    fail "strength"
  if v.radius < 0:
    fail "radius"
```

A later edit of strength on a file with `charged == true` does not charge again (**inferred** from "the first time it is applied to that file"). Disabling clears `beautifyRequested` and keeps `charged` so a re-enable is free.

If the credit charge fails, do not set the flag and do not push the node.

## Render

```text
function apply_skin_smoothing(frame, params) -> bitmap:
  boxes = face_boxes(frame)                 # open detector, not a faceprint
  if boxes is empty or len(boxes) >= 3:
    return frame
  out = frame
  for box in boxes:
    if min(box.w, box.h) < 64:
      continue
    mask = face_mask(frame, box, params)
    blurred = guided_blur(frame, radius_px=params.radius)
    out = composite(out, blurred, mask)
  return out

function face_mask(frame, box, params) -> mask:
  feather_px = params.edge_feather * min(box.w, box.h)
  base = ellipse(box, feather_px)
  if params.mask_area == "WHOLE_FACE":
    return base * params.base_strength
  # Regions: multipliers scale the base strength. Layout of the four
  # regions inside the box is a fixed proportion (inferred):
  # forehead = top 30%, cheeks = mid band, laugh lines = lower cheeks,
  # under-eyes = band just under the upper third.
  m = zeros
  m = paint(m, forehead_region(box), params.base_strength * params.forehead)
  m = paint(m, cheeks_region(box), params.base_strength * params.cheeks)
  m = paint(m, laugh_region(box), params.base_strength * params.laugh_lines)
  m = paint(m, undereye_region(box), params.base_strength * params.under_eyes)
  return feather(m, feather_px)
```

Region rectangles are our layout so the four recovered multipliers do something different. They are **inferred**. `WHOLE_FACE` is the decompiled alternate and ignores multipliers.

No identity embedding is written. Boxes are dropped after the frame. Help-page skips (hats, glasses, hands, low light) are **static-help**. This function only skips when the detector returns nothing, when there are three or more boxes, or when the box is under 64 px. A missed face is a skip, not an error.

Eye Contact is not a branch of this function. A layer may contain both nodes. They do not share an artifact.

## Errors

| Case | Behaviour |
| --- | --- |
| Charge of 5 fails | Effect stays off |
| Detector missing | Fail the frame pass. Do not upload the frame to a vendor to compensate |
| Bad vector | Reject the edit |
| Every frame skipped | Return the original. Report `faces_found: 0` |

The 5-credit meter is local bookkeeping of the agent sentence. There is no recovered HTTP body that submits a skin job.
