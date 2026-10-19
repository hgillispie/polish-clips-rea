# Portrait Lighting

Relights the subject and dims the background with the shared person mask. Effect type `com.descript.portraitLighting`. Analysis: [../descript-analysis/enhance-video-suite.md](../descript-analysis/enhance-video-suite.md). Mask POST: [green-screen.md](green-screen.md). Do not stack with Uplighting unless the operator confirms ([enhance-video-suite.md](enhance-video-suite.md)).

## Parameter vector (decompiled module 107643)

Default preset `[1, 0.58, 0.38, 0.05, -0.05, 0.15, 0]`.

| Index | Name | UI | Default | Range |
| --- | --- | --- | --- | --- |
| 0 | strength | visible | `1` | 0..1 |
| 1 | foregroundBrightness | visible | `0.58` | 0..1 |
| 2 | backgroundBrightness | visible | `0.38` | 0..1 |
| 3 | foregroundWarmth | hidden | `0.05` | recovered default only |
| 4 | backgroundWarmth | hidden | `-0.05` | recovered default only |
| 5 | backgroundBlur | hidden | `0.15` | fed to the radius formula |
| 6 | maskFeather | hidden | `0` | recovered default only |

Agent schema (**static-bundle**) accepts a boolean or `{strength?, foregroundBrightness?, backgroundBrightness?}`. `true` expands to the full 7-vector, including hidden slots. `false` or null disables. Omitted agent numbers use 1 / 0.58 / 0.38 and the hidden defaults.

Tracked feature `aiEffectLighting`. Agent copy says AI credits per use and a speaker on the video. No integer was in that string. Do not label it 10. The mask task it depends on is tracked as `aiEffectGreenScreen` and the green-screen / blur copy says 10 per use of that task. Charge the mask once. A second lighting charge is **unknown**.

Flag: `portraitLightingRequested`, and the mask flag via `ensure_background_mask`.

## Enable

```text
function enable_portrait_lighting(layer, media, params | null) -> void:
  vector = params or [1, 0.58, 0.38, 0.05, -0.05, 0.15, 0]
  if len(vector) != 7:
    fail "portrait lighting params must be 7 numbers"
  clamp vector[0..2] into 0..1
  push VisualEffectNode(type="com.descript.portraitLighting", enabled=true, params=vector)
  media.portraitLightingRequested = true
  if uplighting node is enabled:
    warn_if_portrait_and_uplight
```

## Render (decompiled module 379791)

The client optionally blurs the mask, then runs lighting shader `K`. The radius formula is recovered. The shader body is not. The composite below is our stand-in for `K` (**inferred**), using only the named controls:

```text
function portrait_mask_radius(background_blur) -> number:
  # decompiled: 10 ** (blur * log10(200))
  return 10 ** (background_blur * log10(200))

function apply_portrait_lighting(frame, mask, params) -> bitmap:
  if mask is null:
    return frame
  p = read_portrait(params)
  m = mask
  if p.backgroundBlur != 0:
    m = directional_blur(m, radius_px=portrait_mask_radius(p.backgroundBlur))
  if p.maskFeather != 0:
    m = feather(m, p.maskFeather)
  return lighting_composite(frame, m, p)

function read_portrait(params) -> LightingParams:
  return {
    strength: params[0],
    foregroundBrightness: params[1],
    backgroundBrightness: params[2],
    foregroundWarmth: params[3],
    backgroundWarmth: params[4],
    backgroundBlur: params[5],
    maskFeather: params[6],
    neutralBrightness: 0.58
  }

function lighting_composite(frame, mask, p) -> bitmap:
  # Stand-in for shader K. Not Descript's shader source.
  fg = clamp(mask.r * mask.a, 0, 1)
  neutral = p.neutralBrightness
  subject = grade_brightness_warmth(frame, p.foregroundBrightness, p.foregroundWarmth, neutral)
  background = grade_brightness_warmth(frame, p.backgroundBrightness, p.backgroundWarmth, neutral)
  mixed = lerp(background, subject, fg)
  return lerp(frame, mixed, p.strength)

function grade_brightness_warmth(frame, brightness, warmth, neutral) -> bitmap:
  # brightness == neutral is the recovered default, not "no change" in absolute light.
  # Map 0 → dark, neutral → 1x, 1 → brighter. Exact matrix of shader K is unknown.
  gain = brightness / neutral
  out = frame * gain
  out.r *= 1 + warmth
  out.b *= 1 - warmth
  return clamp(out)
```

At the default background blur `0.15`, the radius is `10 ** (0.15 * log10(200))`, about 2.2 px. Use the formula, not a hard-coded 2.2, so a hidden-parameter edit stays faithful.

Uplighting calls `lighting_composite` with its own defaults and **does not** call `portrait_mask_radius`.

## Errors

| Case | Behaviour |
| --- | --- |
| Mask missing | Draw the original frame. Do not invent a matte |
| params length ≠ 7 | Reject the edit |
| strength outside 0..1 | Clamp on write |
| Speaker missing | Do not POST the mask |

No 10-credit label on this effect's own string.
