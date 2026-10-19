# Uplighting

Brightens the subject using the shared person mask. Effect type `com.descript.uplighting`. Same lighting composite as Portrait Lighting, shorter vector, no mask pre-blur. Analysis: [../descript-analysis/enhance-video-suite.md](../descript-analysis/enhance-video-suite.md).

Do not stack with Portrait Lighting unless the operator confirms ([enhance-video-suite.md](enhance-video-suite.md)).

## Parameter vector (decompiled module 985267)

Default preset `[1, 0.65, 0.65, 0.05, -0.05, 0]`.

| Index | Name | UI | Default |
| --- | --- | --- | --- |
| 0 | strength | visible | `1` |
| 1 | foregroundBrightness | visible | `0.65` |
| 2 | backgroundBrightness | visible | `0.65` |
| 3 | foregroundWarmth | hidden | `0.05` |
| 4 | backgroundWarmth | hidden | `-0.05` |
| 5 | maskFeather | hidden | `0` |

There is no background-blur index. Do not append portrait's `0.15` slot. A 7-vector is a portrait node.

Agent schema: boolean or `{strength?, foregroundBrightness?, backgroundBrightness?}` with defaults 1 / 0.65 / 0.65. `true` expands to the 6-vector (**static-bundle**).

Flag: `uplightingRequested`. Mask: `ensure_background_mask` in [green-screen.md](green-screen.md).

Credits: agent copy says AI credits per use and a speaker. No integer. Do not copy the green-screen 10 onto this slider. The shared mask task is still `aiEffectGreenScreen`.

## Enable and render

```text
function enable_uplighting(layer, media, params | null) -> void:
  vector = params or [1, 0.65, 0.65, 0.05, -0.05, 0]
  if len(vector) != 6:
    fail "uplighting params must be 6 numbers"
  clamp vector[0..2] into 0..1
  push VisualEffectNode(type="com.descript.uplighting", enabled=true, params=vector)
  media.uplightingRequested = true
  if portrait node is enabled:
    warn_if_portrait_and_uplight

function apply_uplighting(frame, mask, params) -> bitmap:
  if mask is null:
    return frame
  p = read_uplight(params)          # no backgroundBlur field
  m = mask
  if p.maskFeather != 0:
    m = feather(m, p.maskFeather)
  # decompiled: same shader K as portrait, no directional pre-blur
  return lighting_composite(frame, m, p)     # portrait-lighting.md
```

`lighting_composite` is the stand-in for shader `K` (**inferred** math, recovered controls). Brightness gain uses this effect's own default `0.65` as the neutral denominator when the grade helper is shared; pass the default in so portrait's `0.58` is not applied by mistake.

```text
function read_uplight(params) -> LightingParams:
  return {
    strength: params[0],
    foregroundBrightness: params[1],
    backgroundBrightness: params[2],
    foregroundWarmth: params[3],
    backgroundWarmth: params[4],
    maskFeather: params[5],
    neutralBrightness: 0.65
  }
```

## Errors

| Case | Behaviour |
| --- | --- |
| 7-vector passed to uplighting | Reject. That is portrait |
| Mask missing | Original frame |
| Both lighting effects confirmed | Apply in list order. Warn already shown |
| Speaker missing | Do not POST the mask |
