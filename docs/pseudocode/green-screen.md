# Green Screen

AI matte. No physical screen. Effect type `com.descript.backgroundRemoval` (`HD.BACKGROUND_REMOVAL`). No parameters. Analysis: [../descript-analysis/enhance-video-suite.md](../descript-analysis/enhance-video-suite.md).

This file owns the shared `background_mask` request. Blur, Portrait Lighting, and Uplighting call `ensure_background_mask` and do not POST on their own.

Self-record is a capture path that can fill the same mask locally: [editor/self-record-bg-remove.md](editor/self-record-bg-remove.md). Imported footage uses the cloud task below. The shader is the same either way.

## Types

```text
BackgroundMask
  asset_id        string
  artifact_id     string | null
  source          "cloud_background_removal" | "local_segmenter" | "chroma_fallback"
  # 1 = person (keep). The green-screen shader reads red * alpha.

GreenScreenNode
  type            "com.descript.backgroundRemoval"
  enabled         boolean
  params          []                  # decompiled module 419488: no parameters
```

Cloud spec `background_mask` (**static-bundle**, offset ~2049550):

```text
endpoint:            background_removal
displayName:         "background effect (removal or blur)"
artifactType:        background_mask
inputArtifactType:   original
type:                blocking
isMtsOnlyEffect:     true
validTypes:          image, video, avatar
effectTypes:         backgroundBlur, backgroundRemoval, uplighting, portraitLighting
trackedFeatureId:    aiEffectGreenScreen
upgradeOrigin:       GenerateBackgroundMask
POST body:           { asset_id }
result:              { asset_id, output_artifact_id }
```

Credit key `green_screen` → `ai_effects`. Agent copy: **10 AI credits per use**, and a speaker associated with the video (**static-bundle**). The same task is tracked as `aiEffectGreenScreen` when blur or lighting requested it. Do not charge 10 again for each shader that reads the mask.

## Ensure one mask

```text
function ensure_background_mask(project_id, media) -> BackgroundMask:
  if media.artifacts.background_mask is present:
    return media.artifacts.background_mask
  if media.local_mask is present:                 # self-record already wrote one
    return media.local_mask

  if not task_accepts_media(SPECS.background_mask, media):
    fail "background_removal does not accept this media"
  if not speaker_associated(media):
    fail "green screen requires a speaker on the video"

  media.backgroundMaskRequested = true
  task = post_cloud_effect(auth, project_id, SPECS.background_mask, { assetId: media.asset_id })
  task = wait_cloud_effect(auth, project_id, SPECS.background_mask, task.id)
  mask = BackgroundMask(
    asset_id=task.result.assetId,
    artifact_id=task.result.artifactIds[0],
    source="cloud_background_removal"
  )
  media.artifacts.background_mask = mask
  return mask
```

`post_cloud_effect` and `wait_cloud_effect` are in [visual-effects-model.md](visual-effects-model.md). HTTP 429 is `state: "hold"`.

Enabling the toggle:

```text
function enable_green_screen(layer, media) -> void:
  push VisualEffectNode(type="com.descript.backgroundRemoval", enabled=true, params=[])
  # chroma key is the solid-color tool. Agent copy prefers it for a flat backdrop.
  if layer has enabled com.descript.chromakey:
    warn "Use chroma key for a solid green or blue screen. Green Screen is the AI matte."
  media.backgroundMaskRequested = true
```

Disabling sets `enabled=false` and, if no other mask consumer remains, clears `backgroundMaskRequested`. The artifact stays so a re-enable does not POST again.

## Shader (decompiled module 419488)

The GLSL entry is named `BackgroundRemoval`. The recovered operation is multiply by the mask's red times the mask's alpha. This is that operation, not a paste of the shader:

```text
function apply_background_removal(content, mask) -> bitmap:
  if mask is null:
    return content                         # fail soft; orchestrator also skips the node
  keep = mask.r * mask.a                   # per pixel, 0..1
  out = content
  out.rgb *= keep
  out.a *= keep
  return out
```

Straight alpha is what the overlay compositor in [editor/layers.md](editor/layers.md) expects. If the captured mask is already a single-channel person probability, set `mask.r = mask.a = probability` before this function.

## Local segmenter

When the operator is offline or the media is a self-record, `source` is `local_segmenter`:

```text
function local_person_mask(bitmap) -> mask:
  # Open person segmenter the implementation chooses (MediaPipe selfie-class or similar).
  # No Descript weights.
  probability = segmenter.infer(bitmap)
  probability = temporal_smooth(probability, previous, alpha=0.6)
  return { r: probability, a: probability }
```

Chroma fallback belongs to self-record when the segmenter fails to load, and to [chroma-key.md](chroma-key.md) when the operator picks a color key. Do not silently switch an imported clip from Green Screen to chroma.

## Errors

| Case | Behaviour |
| --- | --- |
| No speaker | Do not POST |
| 429 | Hold and poll |
| Timeout or other HTTP error | Leave the node enabled, draw the original frame, report the error |
| Empty `artifactIds` | Fail the mask. Do not synthesize one |
| Avatar | Refuse |
| Re-enable with a stored mask | Do not POST. 10 credits were the first use |

The matting network name is **unknown**.
