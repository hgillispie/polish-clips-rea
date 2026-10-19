# Color adjustments

Local grade. No cloud task, no mask, no AI credits. Effect id `com.descript.colorAdjustments` (**static-bundle** allowlist). Descriptor: **decompiled** module 88922. Absent from the cloud property subset `Qa`.

## Parameter index `ft` (decompiled)

| Index | Name | Default |
| --- | --- | --- |
| 0 | Exposure | `0` |
| 1 | Contrast | `0` |
| 2 | Highlights | `0` |
| 3 | Shadows | `0` |
| 4 | BlackPoint | `0` |
| 5 | Saturation | `0` |
| 6 | Vibrancy | `0` |
| 7 | Temperature | `0` |
| 8 | Tint | `0` |
| 9 | TemperatureMode | `1` |

TemperatureMode names are `Helland` and `Linear`. The default stores numeric `1`. Which name equals `1` was not paired in the module summary (**unknown**). Keep the numeric value. Offer both names in the UI only after a later trace maps them. Until then the control is a two-state integer `0` or `1`, labels `mode 0` and `mode 1`.

Presets including Neutral and Warm exist further in the module. Their vectors were not copied into the evidence summary. Do not invent them. The identity preset is the default vector above.

Not in `Qa`, and sibling effects (invert) are described as free GPU. Treat this node as free (**inferred**).

## Render

Curves for exposure, contrast, highlights, shadows, and the two temperature modes were not in the summary. The node still has to grade. These mappings are **inferred** stand-ins so a zero vector is a no-op and the sliders move in the obvious direction. Replace them when a shader trace exists. Do not claim they are Descript's.

```text
ColorAdjustNode
  type    "com.descript.colorAdjustments"
  enabled boolean
  params  number[10]          # index order above

function apply_color_adjustments(frame, params) -> bitmap:
  if len(params) != 10:
    fail "color adjustments need 10 params"
  if params == [0,0,0,0,0,0,0,0,0,1] or params[0:9] == [0]*9:
    return frame                           # mode bit alone does not change pixels at 0 temperature
  e, c, hi, sh, black, sat, vib, temp, tint, mode = params
  out = frame
  out = expose(out, e)                     # multiply by 2**e, e in about -2..2
  out = contrast(out, c)                   # pivot 0.5, gain 1+c
  out = highlights_shadows(out, hi, sh)    # lift top and bottom thirds
  out = black_point(out, black)            # add black into the floor
  out = saturate(out, sat)                 # -1..1 around gray
  out = vibrance(out, vib)                 # saturate low-saturation pixels more
  out = temperature_tint(out, temp, tint, mode)
  return clamp(out)

function temperature_tint(rgb, temp, tint, mode) -> rgb:
  # mode is stored and currently unused in the pixel math until Helland vs Linear is known.
  # Record mode on the node. Do not drop it.
  rgb.r += temp * 0.1 + tint * 0.05
  rgb.b -= temp * 0.1 - tint * 0.05
  return rgb
```

Slider ranges other than "default 0" were not recovered. Clamp exposure and contrast to -2..2 and the rest of the zero-default sliders to -1..1 on write. TemperatureMode only 0 or 1.

## Errors

| Case | Behaviour |
| --- | --- |
| Wrong length | Reject |
| TemperatureMode not 0 or 1 | Reject |
| Non-finite number | Reject |

No POST. No credits. Safe to stack under the mask effects.
