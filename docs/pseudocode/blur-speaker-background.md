# Blur speaker background

Depth-style blur of the background behind the speaker. The person stays sharp. Effect type `com.descript.backgroundBlur` (`HD.BACKGROUND_BLUR`). Uses the shared `background_mask`, not its own endpoint.

UI descriptor (**static-bundle**, chunk 88 ~4893291): name `blur speaker background`, category Media, one parameter `Amount`, `defaultPreset: [0.5]`, empty presets. Help URL on the descriptor: `https://help.descript.com/effects-animations-transitions/blur-speaker-background` (**static-help**).

## Types

```text
BlurSpeakerNode
  type      "com.descript.backgroundBlur"
  enabled   boolean
  params    [amount]              # default [0.5]
```

Credits (**static-bundle**): key `background_blur` → `ai_effects`. Agent copy: **10 AI credits per use**, requires a speaker. That charge is the mask task (`trackedFeatureId` `aiEffectGreenScreen`), shared with Green Screen. If the mask artifact already exists, do not charge another 10 to turn the blur shader on (**inferred** from one `effectTypes` list and one POST).

Flag: `backgroundMaskRequested`. No separate blur flag was recovered.

## Enable and render

```text
function enable_blur_speaker(layer, media, amount | null) -> void:
  a = 0.5 if amount is null else amount
  if a < 0 or a > 1:
    fail "amount must be 0..1"
  push VisualEffectNode(type="com.descript.backgroundBlur", enabled=true, params=[a])
  media.backgroundMaskRequested = true

function apply_background_blur(frame, mask, params) -> bitmap:
  if mask is null:
    return frame
  amount = params[0]                         # default 0.5
  # The UI descriptor does not record the pixel curve (unknown).
  # sigma_px = amount * 24 is our stand-in, not a Descript constant (inferred).
  sigma_px = amount * 24
  blurred = gaussian_blur(frame, sigma_px)
  keep = clamp(mask.r * mask.a, 0, 1)        # same mask channels as BackgroundRemoval
  return lerp(blurred, frame, keep)
```

`ensure_background_mask` runs before the first blurred frame ([green-screen.md](green-screen.md)). A self-record `local_segmenter` mask is valid here.

Amount `0` still samples the mask and returns the sharp frame (`sigma_px` 0). Amount `0.5` is the descriptor default.

## Errors

| Case | Behaviour |
| --- | --- |
| params not length 1 | Reject the edit |
| Mask POST failed | Skip this node, keep the sharp frame |
| No speaker | Do not POST |
| Green Screen also enabled | Legal. Removal and blur both read the same mask; order follows the effect array |

The radius curve can be replaced later without changing the node. Until a bundle trace names it, keep the inferred sigma labeled in the report (`blur_sigma: "inferred_amount_times_24"`).
