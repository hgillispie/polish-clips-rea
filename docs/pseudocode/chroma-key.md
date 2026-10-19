# Chroma key

Classic color key. Local GPU. Not the AI Green Screen and not a `background_removal` POST.

Effect id on the allowlist: `com.descript.chromakey` (**static-bundle**). UI name `chroma key`, category Color. Descriptor and shader: **decompiled** module 514462. Help URL on the descriptor: `https://help.descript.com/effects-animations-transitions/overview#chroma-key` (**static-help**).

Agent copy for Green Screen says to prefer chroma key when the backdrop is a solid color (**static-bundle**).

## Parameters

UI order: key red, key green, key blue, Similarity, Smoothness, Spill.

Default UI key RGB `(0, 255, 74)`, similarity `0.4`, smoothness `0.08`, spill `0.1`.

The stored preset's first three slots are `fromUiValue` of those channels, not the raw bytes 0 / 255 / 74. Round-trip helpers on the descriptor convert with `toUiValue` / `fromUiValue`. Polish Clips stores the UI bytes plus the three floats, and converts at the shader boundary:

```text
ChromaKeyNode
  type            "com.descript.chromakey"
  enabled         boolean
  key_rgb         [number, number, number]     # 0..255 UI, default [0, 255, 74]
  similarity      number                       # default 0.4
  smoothness      number                       # default 0.08
  spill           number                       # default 0.1
```

Index enum on the descriptor is Red, Green, Blue, then Similarity, Smoothness, Spill. A different Red/Green/Blue/Range/Intensity enum sits beside the HD map and is **not** this effect. Do not reuse it.

## Shader (decompiled behaviour, not GLSL source)

```text
function apply_chroma_key(bitmap, node) -> bitmap:
  key = node.key_rgb
  out = copy(bitmap)
  for pixel in out:
    dist = uv_distance(pixel.rgb, key)          # chroma plane, not RGB euclidean
    if node.smoothness <= 0:
      t = 0 if dist <= node.similarity else 1
    else:
      t = clamp((dist - node.similarity) / node.smoothness, 0, 1)
    alpha_keep = pow(t, 1.5)                    # recovered exponent
    pixel.a *= alpha_keep
    pixel.rgb = despill(pixel.rgb, key, node.spill, alpha_keep)
  return out

function despill(rgb, key, spill, alpha_keep) -> rgb:
  # Recovered intent: desaturate the key color on pixels that are partly keyed.
  # The exact mix was not extracted as a formula. Scale by spill (default 0.1).
  if spill <= 0 or alpha_keep >= 1:
    return rgb
  toward = average of the two channels that are not the key's dominant channel
  dominant = index of max(key)
  rgb[dominant] = lerp(rgb[dominant], toward, spill * (1 - alpha_keep))
  return rgb

function uv_distance(rgb, key) -> number:
  # Convert both colors to a UV chroma pair (U = B-Y, V = R-Y) and return
  # the planar distance, normalized so the default similarity 0.4 is meaningful
  # on a green screen. Implementation picks one standard YUV matrix and stays with it.
  return length(uv(rgb) - uv(key))
```

`pow(..., 1.5)` and the `(dist - similarity) / smoothness` gate are **decompiled**. `uv_distance`'s matrix and `despill`'s channel mix are **inferred** stand-ins around those recovered operations. Label them in code comments so a later trace can replace them.

No AI credits. No speaker check. No `backgroundMaskRequested`.

## Errors

| Case | Behaviour |
| --- | --- |
| Key channel outside 0..255 | Reject |
| similarity or smoothness or spill outside 0..1 | Clamp on write |
| smoothness 0 | Hard key, as the branch above |
| Green Screen also on | Warn, both may run ([enhance-video-suite.md](enhance-video-suite.md)) |

Self-record's chroma fallback uses this function when the segmenter is missing, with the same defaults unless the operator picked another key color.
