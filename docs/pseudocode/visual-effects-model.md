# Visual effects model

Ordered effect nodes on a visual layer, plus the media-ref flags that schedule cloud artifacts. This is the foundation for the Look Good suite. It is not a trace of Descript's document schema. Names, ids, and HTTP shapes are from the web client build `react19/9a29d61183bce669600a9dd9a1f8588d708becac` (2026-10-19).

Analysis: [../descript-analysis/enhance-video-suite.md](../descript-analysis/enhance-video-suite.md).

`VisualLayer.effects` is declared in [editor/layers.md](editor/layers.md). An empty list is the MVP. A non-empty list is this spec and is later than the polish-clip pipeline.

## HD type ids (static-bundle, chunk 88 ~3772069)

```text
HD
  BACKGROUND_BLUR        = "com.descript.backgroundBlur"
  BACKGROUND_REMOVAL     = "com.descript.backgroundRemoval"
  EYE_CONTACT            = "com.descript.eyeContact"
  CENTER_ACTIVE_SPEAKER  = "com.descript.speakerFocus"
  UPLIGHTING             = "com.descript.uplighting"
  PORTRAIT_LIGHTING      = "com.descript.portraitLighting"
```

String constants next to that enum, not members of it: `com.descript.glassBlur`, `com.descript.checkerboardMask`, `com.descript.glow`.

Allowlist ids used by local effects in this spec:

```text
CHROMA_KEY             = "com.descript.chromakey"
COLOR_ADJUSTMENTS      = "com.descript.colorAdjustments"
STUDIO_SOUND           = "com.descript.studioSound"     # audio, not a visual HD member
```

Skin smoothing has no recovered `com.descript.*` string. The node kind is `skin_smoothing`. The minified binding is `mo.WaC` (**static-bundle**). Do not invent a wire string.

## Node

```text
VisualEffectNode
  id            string
  type          string          # an HD wire string, CHROMA_KEY, COLOR_ADJUSTMENTS, or "skin_smoothing"
  enabled       boolean
  params        number[]        # descriptor order; [] when the effect has no parameters
  preset_name   string | null

# Array order is apply order. Index 0 is closest to the source pixels.
# Descript's Properties panel top-to-bottom direction was not in the bundle slices (unknown).
```

Default vectors recovered from descriptors (**decompiled** unless noted):

| type | params default | Source |
| --- | --- | --- |
| `com.descript.eyeContact` | `[]` | module 35972 |
| `com.descript.speakerFocus` | `[]` | module 916791 |
| `com.descript.backgroundRemoval` | `[]` | module 419488 |
| `com.descript.backgroundBlur` | `[0.5]` | static-bundle ~4893291, Amount |
| `com.descript.portraitLighting` | `[1, 0.58, 0.38, 0.05, -0.05, 0.15, 0]` | module 107643 |
| `com.descript.uplighting` | `[1, 0.65, 0.65, 0.05, -0.05, 0]` | module 985267 |
| `com.descript.chromakey` | key RGB UI `(0, 255, 74)`, then `0.4, 0.08, 0.1` | module 514462 |
| `com.descript.colorAdjustments` | nine zeros, then TemperatureMode `1` | module 88922 |
| `skin_smoothing` | `[0.4, 3, 0.0212, REGIONS, 1, 0.3, 0.3, 2.5]` | module 351916 |

## Media-ref flags (static-bundle)

Set on the media ref when the operator enables the effect. Clearing the flag stops render use. It does not delete an artifact already stored.

```text
VideoOrImageFlags
  eyeContactRequested          boolean
  backgroundMaskRequested      boolean
  portraitLightingRequested    boolean
  uplightingRequested          boolean
  beautifyRequested            boolean
  speakerFocusRequested        boolean

AudioFlags
  speechEnhanceEnabled         boolean
  studioSoundIntensity         number | null    # present in the client; not a field of the speech_enhancement POST
  lipSyncRequested             boolean          # imputation / Video Regenerate
  translationLipSyncRequested  boolean          # dub lip-sync, different variant
```

## Cloud task registry (static-bundle)

Host for these paths: `https://api.descript.com`. Not `descriptapi.com`. Paths are not under `/v1`.

```text
CloudEffectSpec
  endpoint                 string
  name                     string
  displayName              string
  artifactType             string
  inputArtifactType        "original"
  type                     "artifact" | "blocking"
  isMtsOnlyEffect          boolean
  validTypes               string[]       # "video" | "audio" | "image" | "avatar"
  effectTypes              string[]       # HD wire strings, possibly empty
  trackedFeatureId         string
  upgradeOrigin            string

SPECS
  eye_contact:
    endpoint eye_gaze_correction
    name eye_contact
    displayName "Eye Contact"
    artifactType eye_contact
    type artifact
    isMtsOnlyEffect true
    validTypes [video]
    effectTypes [com.descript.eyeContact]
    trackedFeatureId aiEffectEyeContact
    upgradeOrigin GenerateEyeContact          # kebab generate-eye-contact
  background_mask:
    endpoint background_removal
    name background_mask
    displayName "background effect (removal or blur)"
    artifactType background_mask
    type blocking
    isMtsOnlyEffect true
    validTypes [image, video, avatar]
    effectTypes [
      com.descript.backgroundBlur,
      com.descript.backgroundRemoval,
      com.descript.uplighting,
      com.descript.portraitLighting
    ]
    trackedFeatureId aiEffectGreenScreen
    upgradeOrigin GenerateBackgroundMask
  center_active_speaker:
    endpoint face_tracking
    name center_active_speaker
    displayName "center active speaker"
    artifactType face_tracking
    type artifact
    validTypes [video]
    effectTypes [com.descript.speakerFocus]
    trackedFeatureId aiEffectCenterActiveSpeaker
    upgradeOrigin CenterActiveSpeaker
    displayInSuperToast false
  imputation_lip_sync:
    endpoint lip_sync
    name imputation_lip_sync
    displayName "Video Regenerate"
    artifactType imputation_lip_sync
    type artifact
    validTypes [audio]
    variant imputation
    displayInSuperToast false
  translation_lip_sync:
    endpoint lip_sync
    name translation_lip_sync
    displayName "lip-sync"
    artifactType translation_lip_sync
    type artifact
    validTypes [audio]
    variant translation
    displayInSuperToast false
  studio_sound:
    endpoint speech_enhancement
    name studio_sound
    displayName "Studio Sound"
    artifactType speech_enhanced
    type blocking
    validTypes [audio]
    effect id string com.descript.studioSound
    trackedFeatureId aiEffectStudioSound
    upgradeOrigin GenerateStudioSound
    displayInSuperToast false
```

`type: "blocking"` means the renderer does not draw that effect until the artifact exists (**inferred** from the word; the string itself is static-bundle). `type: "artifact"` means attach the result and draw when it is present (same caveat).

`inputArtifactType: "original"` means each of these jobs reads the original asset. They do not chain on the server. Stacking is a client composite.

## POST and poll

Shared helper, **static-bundle** (factory beside the eye-contact spec, offset ~2054622):

```text
function post_cloud_effect(auth, project_id, spec, payload, type_headers | null) -> task:
  body = spec.payload_json(payload)          # per-effect functions below
  response = POST https://api.descript.com/projects/{project_id}/{spec.endpoint}
    headers: Authorization from the operator session, Content-Type: application/json
    body: body
    typeHeaders: type_headers                 # argument exists; contents unknown
  return map_result(response, spec.result_json)

function poll_cloud_effect(auth, project_id, spec, task_id) -> task:
  try:
    response = GET https://api.descript.com/projects/{project_id}/{spec.endpoint}/{task_id}
    return map_result(response, spec.result_json)
  catch error:
    if error.status == 429:
      return { id: task_id, state: "hold" }  # not a failure
    throw error

function map_result(response, result_json) -> task:
  task = copy of response
  if response.result is present:
    task.result = result_json(response.result)
  else:
    task.result = null
  return task

function wait_cloud_effect(auth, project_id, spec, task_id, timeout_seconds=900) -> task:
  delay = 2
  deadline = now + timeout_seconds
  while now < deadline:
    task = poll_cloud_effect(...)
    if task.state == "hold":
      sleep delay
      delay = min(30, delay * 1.5)
      continue
    if task.result is not null:
      return task
    # Other state strings were not named in the helper (unknown).
    sleep delay
    delay = min(30, delay * 1.5)
  fail "cloud task timed out"
```

The POST return is the same task object the poll reads. The hold body echoes `id`. Treat that `id` as the poll key (**static-bundle** on the 429 path; the success field name is the same object the helper spreads).

Result mappers:

| Spec | Result JSON | Mapped |
| --- | --- | --- |
| eye_contact | `{asset_id, artifact_ids}` | `{assetId, artifactIds}` plural |
| background_mask, face_tracking, both lip_sync | `{asset_id, output_artifact_id}` | `{assetId, artifactIds: [output_artifact_id]}` |
| studio_sound | `{speech_enhancement_audio_asset_id, speech_enhancement_audio_artifact_id}` | `{assetId, artifactIds: [artifact]}` |

Payloads are specified in the per-effect files. Eye contact, background removal, and face tracking send `{asset_id}` only.

## Eligibility (static-bundle)

```text
function task_accepts_media(spec, media) -> boolean:
  kind_ok =
       ("audio" in spec.validTypes and media.kind == "audio")
    or ("video" in spec.validTypes and media.kind == "video")
    or ("image" in spec.validTypes and media.kind == "image")
    or ("avatar" in spec.validTypes and media.kind == "avatar")
  if not kind_ok:
    return false
  if spec.isEligibleMediaRef is null:
    return true
  return spec.isEligibleMediaRef(media)
```

`isEligibleMediaRef` is set for eye contact (minified `n.kx`) and center active speaker (minified `n.l_`). Bodies were not recovered. Agent copy for the 10-credit cloud effects says a speaker must be associated with the video. Polish Clips enforces that as: video, a transcript with at least one non-ignored word, and a single labeled speaker on that span. That predicate is **inferred**.

Avatar is a legal `validTypes` entry for the mask task. This editor has no avatar track. `task_accepts_media` returns false for avatar until one exists.

## Apply on a frame

```text
function apply_visual_effects(bitmap, effects, artifacts, t) -> bitmap:
  out = bitmap
  for effect in effects:                  # index 0 first
    if not effect.enabled:
      continue
    out = apply_one(out, effect, artifacts, t)
  return out

function apply_one(bitmap, effect, artifacts, t) -> bitmap:
  switch effect.type:
    com.descript.eyeContact:
      return apply_eye_contact(bitmap, artifacts.eye_contact)          # eye-contact.md
    com.descript.backgroundRemoval:
      return apply_background_removal(bitmap, artifacts.background_mask)
    com.descript.backgroundBlur:
      return apply_background_blur(bitmap, artifacts.background_mask, effect.params)
    com.descript.portraitLighting:
      return apply_portrait_lighting(bitmap, artifacts.background_mask, effect.params)
    com.descript.uplighting:
      return apply_uplighting(bitmap, artifacts.background_mask, effect.params)
    com.descript.chromakey:
      return apply_chroma_key(bitmap, effect.params)
    com.descript.colorAdjustments:
      return apply_color_adjustments(bitmap, effect.params)
    com.descript.speakerFocus:
      return apply_speaker_focus(bitmap, artifacts.face_tracking, t)
    skin_smoothing:
      return apply_skin_smoothing(bitmap, effect.params)
    else:
      warn "effect not implemented: " + effect.type
      return bitmap
```

[editor/layers.md](editor/layers.md) calls `apply_visual_effects` on the source bitmap before crop and transform. Export uses the same `composite_frame`, so the effects are in the preview and in the file.

Mask consumers share one artifact. See [green-screen.md](green-screen.md) `ensure_background_mask`. Do not POST `background_removal` once per effect.

## Credits (static-bundle categories)

| Key | Category | Integer in the agent schema |
| --- | --- | --- |
| `eye_contact` | `ai_effects` | 10 per use |
| `green_screen` | `ai_effects` | 10 per use |
| `background_blur` | `ai_effects` | 10 per use |
| `skin_smoothing` | `ai_effects` | 5 per file, first apply |
| `center_active_speaker` | `ai_effects` | not in that sentence |
| `studio_sound` | `ai_effects` | not an integer in the visual schema |
| portrait / uplight | agent says "AI credits per use" | integer absent. Do not assume 10 |

The mask task's `trackedFeatureId` is `aiEffectGreenScreen` even when the shader is blur or lighting. Portrait's own tracked feature in the lighting copy is `aiEffectLighting`. Whether lighting adds a second charge on top of the mask is **unknown**. Record both ids on the report and do not double-count unless a live account shows two charges.

Paywall behavior string `PreSeason6EyeContactGreenScreenStudioSoundPaywallBehavior` covers Eye Contact, Green Screen, and Studio Sound.

## Stylize later

Do not implement these in the Look Good path: `glfx.triangleBlur`, `com.descript.filmGrain`, `com.descript.invert`, `com.descript.vignette`, `com.descript.threshold`, `com.descript.colorTone`, `com.descript.infrared`, `com.descript.selectiveColor`, `com.descript.vhs`, `com.descript.ascii`, `com.descript.pixelation`, `glfx.zoomBlur`, `com.descript.glassBlur`, `com.descript.checkerboardMask`, `com.descript.glow`. Invert, infrared, and threshold are free GPU effects in the agent schema (**static-bundle**). They still wait.

## Errors

| Case | Behaviour |
| --- | --- |
| Effect type unknown | Skip the node, warn once |
| `params` length does not match the default vector | Reject the edit before render |
| Cloud 429 | `state: "hold"`, keep polling |
| Cloud task timeout | Leave the flag set, draw the frame without that effect, surface the error |
| `result` missing and state is not `hold` | Keep polling until timeout. Do not invent a failed state |
| Avatar media | Refuse the mask task |

A public-API `POST /v1/jobs/agent` 402 is a different host. These project routes were not traced for 402 in this pass (**unknown**). If the session returns a payment error, stop the effect and do not retry in a loop.
