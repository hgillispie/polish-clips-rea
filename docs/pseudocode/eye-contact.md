# Eye Contact

Cloud gaze correction, then a parameter-less effect. Type `com.descript.eyeContact`. Not skin smoothing. Not Video Regenerate.

Analysis: [../descript-analysis/eye-contact.md](../descript-analysis/eye-contact.md). POST helper: [visual-effects-model.md](visual-effects-model.md).

Later than the polish-clip MVP. Specified, not a research note.

## Contract (static-bundle, offset ~2054012)

```text
EyeContactNode
  type       "com.descript.eyeContact"
  enabled    boolean
  params     []                     # decompiled module 35972: parameters [] , defaultPreset []

# Media flag
video.eyeContactRequested = true | false

SPECS.eye_contact
  endpoint            eye_gaze_correction
  name                eye_contact
  displayName         "Eye Contact"
  artifactType        eye_contact
  inputArtifactType   original
  type                artifact
  isMtsOnlyEffect     true
  validTypes          [video]
  effectTypes         [com.descript.eyeContact]
  trackedFeatureId    aiEffectEyeContact
  upgradeOrigin       GenerateEyeContact     # kebab generate-eye-contact
  surface             EyeContact

POST /projects/{projectId}/eye_gaze_correction
  body: { asset_id }

result JSON { asset_id, artifact_ids }  →  { assetId, artifactIds }
# Plural artifact_ids. Do not read output_artifact_id on this task.
```

Poll: `GET /projects/{projectId}/eye_gaze_correction/{taskId}`. HTTP 429 → `{id, state: "hold"}`.

Credits: **10 AI credits per use**. Category `eye_contact` → `ai_effects`. Agent copy also requires a speaker associated with the video. Paywall string `PreSeason6EyeContactGreenScreenStudioSoundPaywallBehavior`.

UI category Media. Embedded help URL `https://help.descript.com/effects-animations-transitions/eye-contact` (**static-help**). There is no strength slider to build.

`isEligibleMediaRef` (`n.kx`) was not recovered. Our gate is the inferred speaker rule in the visual-effects model: video, non-ignored words, one speaker on the clip.

## Steps

```text
function enable_eye_contact(layer, media) -> void:
  if media.kind != "video":
    fail "eye contact is video only"
  if not speaker_associated(media):
    fail "eye contact requires a speaker associated with the video"
  push VisualEffectNode(type="com.descript.eyeContact", enabled=true, params=[])
  media.eyeContactRequested = true

function ensure_eye_contact(project_id, media) -> artifact:
  if media.artifacts.eye_contact is present:
    return media.artifacts.eye_contact          # toggle off/on does not POST again
  task = post_cloud_effect(
    auth, project_id, SPECS.eye_contact, { assetId: media.asset_id }
  )
  task = wait_cloud_effect(auth, project_id, SPECS.eye_contact, task.id)
  if task.result is null or task.result.artifactIds is empty:
    fail "eye_gaze_correction returned no artifact"
  media.artifacts.eye_contact = task.result
  report credits: 10, category ai_effects, feature aiEffectEyeContact
  return task.result

function apply_eye_contact(frame, artifact) -> bitmap:
  if artifact is null:
    return frame
  # The public client has no landmark pass and no parameter.
  # The artifact is the corrected picture (or a delta the renderer samples).
  # Pixel format of eye_contact was not in the result mapper (unknown).
  corrected = sample_artifact(artifact, frame.time)
  if corrected is null:
    return frame                              # fail soft for this frame
  return corrected
```

`sample_artifact` is the renderer binding. If the artifact is a full replacement video, return that frame. If a later trace shows a partial overlay, composite it. Do not run a local gaze warp in the default path and call it this effect. A local open model may sit behind a feature flag `eye_contact_local`; label its output `source: "local"` and do not claim the 10-credit cloud artifact.

Disable:

```text
function disable_eye_contact(layer, media) -> void:
  node.enabled = false
  media.eyeContactRequested = false
  # keep media.artifacts.eye_contact
```

## Failure

| Case | Behaviour |
| --- | --- |
| Image, audio, or avatar | Fail at enable. `validTypes` is video |
| No speaker | Do not POST |
| Empty `params` violated (caller sent a strength) | Reject. The descriptor's parameter list is empty |
| 429 | Hold and poll |
| Timeout or empty `artifactIds` | Leave the node enabled, draw the original frame, show the error |
| Payment error from the session | Stop. Do not retry. 10 credits were not spent if the POST never returned a task |
| Re-enable with artifact present | No second POST, no second 10 |

Server model name: **unknown**. No weights in the repo.

Kebab `generate-eye-contact` is the upgrade origin an agent action uses. The direct UI path is the flag plus this POST, not the public `POST /v1/jobs/agent` route.
