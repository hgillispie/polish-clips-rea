# Center active speaker

Reframe toward the person who is talking. Effect type `com.descript.speakerFocus` (`HD.CENTER_ACTIVE_SPEAKER`). UI parameters: none (**decompiled** module 916791 and module 284685).

Cloud task (**static-bundle**, offset ~2050300):

| Field | Value |
| --- | --- |
| name | `center_active_speaker` |
| displayName | `center active speaker` |
| endpoint | `face_tracking` |
| artifactType | `face_tracking` |
| inputArtifactType | `original` |
| type | `artifact` |
| validTypes | `video` |
| displayInSuperToast | `false` |
| POST | `{asset_id}` |
| result | `{asset_id, output_artifact_id}` → one artifact id |
| flag | `speakerFocusRequested` |
| trackedFeatureId | `aiEffectCenterActiveSpeaker` |
| upgradeOrigin | `CenterActiveSpeaker` |
| isEligibleMediaRef | minified `n.l_`, body unknown |

Kebab ids: `center-active-speaker` and `center-active-speaker-v2` (**static-bundle**). What v2 changes is **unknown**. Polish Clips implements one node. A probe can record which kebab the client sends; do not invent a second algorithm.

Credit key `center_active_speaker` → `ai_effects`. Underlord's variant `center_active_speaker_underlord` → `["ai_effects", "ai_agent"]`. No "10 AI credits" integer was on this task.

Schema symbol `ActiveSpeakerFramesEncodedSchema` is present in chunks 760 and 1356. Fields were not recovered (**unknown**). The render below takes a decoded list. The decoder is a stub until a trace names the fields.

Audio and video need to be the same talking-head clip. The task's `validTypes` is video only. The client still needs the soundtrack to know who is active; that join is **inferred** from the effect's name plus the schema symbol, not from a recovered function.

## Failure copy (static-bundle)

```text
function face_tracking_error(failure_reason) -> string:
  switch failure_reason:
    "face-detection:no-faces":           return "No faces were detected"
    "video:max-duration-exceeded":       return "Video duration is longer than 1.5 hours"
    "video:unsupported-format":          return "Video format is not supported"
    default:                             return "Unexpected error has occurred"
```

Those three codes and the default sentence are the client's switch. Duration over 1.5 hours fails before POST.

## Enable, POST, apply

```text
ActiveSpeakerFrame
  time_seconds     number
  face_box         [x, y, w, h]          # 0..1 of the frame; field names inferred
  speaker_id       string | null

function enable_center_active_speaker(layer, media) -> void:
  if media.duration_seconds > 1.5 * 3600:
    fail face_tracking_error("video:max-duration-exceeded")
  push VisualEffectNode(type="com.descript.speakerFocus", enabled=true, params=[])
  media.speakerFocusRequested = true

function ensure_face_tracking(project_id, media) -> artifact:
  if media.artifacts.face_tracking is present:
    return media.artifacts.face_tracking
  if not task_accepts_media(SPECS.center_active_speaker, media):
    fail "face_tracking requires video"
  task = post_cloud_effect(auth, project_id, SPECS.center_active_speaker, { assetId: media.asset_id })
  task = wait_cloud_effect(...)
  if task.failureReason:
    fail face_tracking_error(task.failureReason)
  media.artifacts.face_tracking = task.result
  return task.result

function apply_speaker_focus(frame, artifact, t) -> bitmap:
  if artifact is null:
    return frame
  frames = decode_active_speaker_frames(artifact)    # stub; schema unknown
  sample = frame at t, or the nearest sample
  if sample is null or sample.face_box is null:
    return frame
  # Shift and scale so the face box center lands on the frame center.
  # Crop is the VisualLayer crop. Do not destroy pixels outside the box; pan the source.
  return pan_to_center(frame, sample.face_box)
```

`decode_active_speaker_frames` returns `[]` and logs `schema unknown` until the encoded fields are traced. The node then no-ops instead of guessing boxes. A local face detector may fill `ActiveSpeakerFrame` behind a feature flag; label those boxes `source: "local"` so they are not confused with the `face_tracking` artifact.

`pan_to_center` writes the layer crop for that time. It runs after the mask and lighting nodes when the recommended order in [enhance-video-suite.md](enhance-video-suite.md) is used, and after them only if the operator left this node last.

## Errors

| Case | Behaviour |
| --- | --- |
| `face-detection:no-faces` | Show the client sentence. Leave the frame uncropped |
| Longer than 1.5 hours | Fail at enable. Do not POST |
| Unsupported format | Show the client sentence |
| Schema undecoded | No-op the reframe. Do not POST a second time |
| 429 | Hold and poll, same helper as the other cloud effects |

This effect does not set `backgroundMaskRequested` and does not read `background_mask`.
