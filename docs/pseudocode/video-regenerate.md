# Video Regenerate

**Video Regenerate is `lip_sync` with `variant: "imputation"`.** It rebuilds the picture of a talking-head section so the mouth and face match audio that already changed. It is not a prompt-to-video generator.

The cloud task `displayName` is the string `Video Regenerate`. The task `name` is `imputation_lip_sync`. Analysis: [../descript-analysis/video-regenerate.md](../descript-analysis/video-regenerate.md).

Translate / dub uses the **same** endpoint with `variant: "translation"` and `displayName` `lip-sync`. Generate-from-prompt is kebab `generate-video`, a different action. Neither is implemented here.

Later than the polish-clip MVP. Depends on a consented voice when the audio itself is synthetic: [voice-consent.md](voice-consent.md).

## What each name is

| Name | Symbol | In this spec |
| --- | --- | --- |
| Video Regenerate | `imputation_lip_sync`, variant `imputation` | Yes |
| Lip-sync (dub) | `translation_lip_sync`, variant `translation` | Specified only so it is not called by mistake |
| Generate video | kebab `generate-video`, credit `ai_gen_video` → `ai_media_generation` | No |
| Regenerate audio | credit `ai_regenerate_audio` → `ai_speech` | The audio artifact this POST consumes, not this POST |
| Smooth jump cuts | kebab `smooth-jump-cuts`, credit `smooth_jump_cuts` → `ai_editing` | A different action. It may precede a regenerate. It does not set `variant` |

There is no recovered enum `audio_only` / `audio_and_video` (**unknown** in this bundle). Those words are older help text (**static-help**). The bundle choice is: skip `lip_sync`, or POST variant `imputation`.

## Types

```text
ImputationRequest
  project_id                  string
  composition_id              string
  asset_id                    string          # video asset
  audio_artifact_id           string          # speech for the section
  imputation_audio_time_range { start, end }  # seconds on the audio artifact
  prefix_urls                 string[]
  suffix_urls                 string[]
  to_be_replaced_urls         string[]
  consent_visual              boolean         # modal gate below
  voice_profile_id            string | null   # required only when audio is synthetic

# POST body, static-bundle offset ~2054622
{
  asset_id,
  audio_artifact_id,
  audio_artifact_time_range,     # from imputationAudioTimeRange
  prefix_urls,
  suffix_urls,
  to_be_replaced_urls,
  variant: "imputation",
  composition_id
}

Translation body (do not send from this feature), offset ~2056894
{
  asset_id,
  audio_artifact_id,
  audio_artifact_time_range,     # from dubAudioTimeRange, not imputationAudioTimeRange
  prefix_urls: [],
  suffix_urls: [],
  to_be_replaced_urls,
  variant: "translation",
  composition_id
}
```

Task record: `artifactType` `imputation_lip_sync`, `type` `artifact`, `validTypes` `["audio"]`, `inputArtifactType` `original`, `surface` `LipsyncModel`, `displayInSuperToast` false. `validTypes` audio means the driving artifact is audio. `asset_id` is still sent. The result is `{assetId, artifactIds: [output_artifact_id]}`.

Media flag when this path is armed: `lipSyncRequested`. Dub sets `translationLipSyncRequested` instead.

If `additionalData` is missing, the client throws `"additionalData is required for lip sync"` (surface `AITools`). Our `post` builds that object and fails the same way when any required field is null.

## Gates

```text
function can_impute(request, profile) -> void:
  if request.composition_id is null:
    fail "composition_id is required"
  if request.audio_artifact_id is null:
    fail "audio artifact is required"
  if request.imputation_audio_time_range.end <= request.imputation_audio_time_range.start:
    fail "time range is empty"
  if request.to_be_replaced_urls is empty:
    fail "to_be_replaced_urls is required"
  if not request.consent_visual:
    fail "visual regenerate confirmation is required"
  if audio_is_synthetic(request.audio_artifact_id):
    if not can_synthesize(profile, ""):          # voice-consent.md
      fail "consent missing"
```

`consent_visual` is our flag for the client symbol `HIDE_REGENERATE_LIP_SYNC_CONFIRMATION_MODAL` (**static-bundle**: a confirmation modal exists). The modal's paragraph was not recovered. Show: "This rebuilds the face in the selected section to match the new audio." A stored hide-bit skips the modal the next time and still counts as consent for that project. Help-page wording about visual performance is **static-help**; the modal symbol is the bundle evidence.

Voice consent is the other gate and only applies when the audio artifact was synthesized. A punch-in recording does not need a `VoiceProfile`. It still needs `consent_visual` before the picture POST.

## Range

```text
function build_imputation(composition, range, audio_artifact) -> ImputationRequest:
  clip = video clip containing range
  if clip is null:
    fail "range is not on a video clip"
  if range crosses a second clip or a sequence boundary:
    fail "range must stay inside one clip"
  if every word in range is ignored:
    fail "range is ignored-only"
  if count_speakers(range) > 1:
    fail "one speaker"
  # Sequences are rejected because nesting is off (timeline-model) and this
  # task was not recovered as accepting a sequence media id (inferred).
  prefix, suffix, replace = urls_around(clip, range)
  return ImputationRequest(
    asset_id=clip.media_id,
    audio_artifact_id=audio_artifact.id,
    imputation_audio_time_range=audio_range_for(audio_artifact, range),
    prefix_urls=prefix,
    suffix_urls=suffix,
    to_be_replaced_urls=replace,
    composition_id=composition.id,
    ...
  )
```

`prefix_urls` and `suffix_urls` are the context the payload names. Filling them with the neighboring original media URLs is **inferred** from the field names. Empty arrays are what the **translation** variant forces; imputation forwards whatever `additionalData` holds, so we send the neighbor URLs rather than `[]`. If the range starts at 0, `prefix_urls` may be empty. `to_be_replaced_urls` may not.

Language and max length were not in this slice. Do not enforce a 250-character cap from help pages. Do refuse an empty range.

## POST, poll, apply

```text
function regenerate_video(request, profile) -> LipSyncOutcome:
  can_impute(request, profile)
  media.lipSyncRequested = true
  media.translationLipSyncRequested = false
  task = post_cloud_effect(auth, request.project_id, SPECS.imputation_lip_sync, {
    assetId: request.asset_id,
    artifactId: request.audio_artifact_id,
    additionalData: {
      imputationAudioTimeRange: request.imputation_audio_time_range,
      prefixUrls: request.prefix_urls,
      suffixUrls: request.suffix_urls,
      toBeReplacedUrls: request.to_be_replaced_urls,
      compositionId: request.composition_id
    }
  })
  task = wait_cloud_effect(...)
  if task.result is null:
    return failed(task)
  return pending_review(task.result)

# payload_json for this spec is the imputation object above.
# Do not set variant to "translation" in this function.
```

Credit keys to record, without inventing an integer: `lip_sync` → `ai_media_generation` for this POST. If we also synthesized the audio, that earlier step records `ai_regenerate_audio` → `ai_speech`. `ai_regenerate_video` is a separate key in the same media-generation category; the imputation task's own name is `lip_sync`. Attach `lip_sync` to this outcome. Do not also attach `ai_gen_video`.

## Review actions (static-bundle symbols)

```text
LipSyncOutcome
  state        "pending_review" | "applied" | "failed" | "dismissed"
  result       { assetId, artifactIds } | null
  error_type   string | null          # LipSyncGenerationErrorType members unknown
  restore_to   artifact id of the pre-imputation picture

function apply_lip_sync(outcome, clip) -> void:
  # symbol APPLY_LIP_SYNC
  if outcome.state != "pending_review":
    fail "nothing to apply"
  outcome.restore_to = clip.current_picture_artifact
  clip.picture_artifact = outcome.result.artifactIds[0]
  outcome.state = "applied"

function fresh_lip_sync(outcome, request, profile) -> LipSyncOutcome:
  # symbol FRESH_LIP_SYNC
  return regenerate_video(request, profile)

function dismiss_failed(outcome) -> void:
  # symbol family DISMISS_FAILED_LIP_SYNC
  outcome.state = "dismissed"
  # clip picture unchanged

function restore(outcome, clip) -> void:
  # inputArtifactType "original" means the source was not overwritten on the server.
  # Putting the previous picture back is inferred from that, not a button label in the slice.
  if outcome.restore_to is null:
    fail "nothing to restore"
  clip.picture_artifact = outcome.restore_to
  outcome.state = "dismissed"
```

Segment symbols `LIP_SYNC_SEGMENTS` mean a long selection can come back as several pieces. Apply is per segment. A failed segment can be dismissed without discarding a sibling that succeeded. `EditBoundaryRegenerationHelpers` is named and not specified; call the range builder above and do not stub a hidden helper.

## Quality

No lip-sync scorer was in the client. Before `apply_lip_sync`, the operator previews the artifact. Optional local check, **inferred**, off by default:

```text
function lip_sync_quality_gate(preview) -> "pass" | "warn":
  # Open metric the implementation chooses (offset of mouth motion vs audio envelope).
  # Not Descript's training scorer. A warn offers Fresh, Dismiss, or Apply anyway.
  if preview.sync_offset_ms > 80:
    return "warn"
  return "pass"
```

80 ms is our threshold, not a recovered constant.

## Translation, not this feature

```text
function regenerate_translation(...):
  fail "translation lip-sync is out of this spec"
  # If a later spec implements it, the body must set
  # variant "translation", prefix_urls [], suffix_urls [],
  # audio_artifact_time_range from dubAudioTimeRange,
  # and translationLipSyncRequested = true.
  # Symbol GENERATE_TRANSLATION_LIP_SYNC.
```

## Generate video, not this feature

Kebab `generate-video` is in the generative action set with `generate-image`, `generate-music`, `generate-sfx`, and `youtube-thumbnail` (**static-bundle**). It has no `variant: "imputation"`. Do not route a prompt through `lip_sync`.

## Errors

| Case | Behaviour |
| --- | --- |
| Missing additionalData field | Fail before POST with the lip-sync required message |
| `variant` anything but `imputation` | Fail. This function does not dub |
| Synthetic audio, `can_synthesize` false | Fail. No POST |
| `consent_visual` false | Fail. No POST |
| Empty `to_be_replaced_urls` | Fail |
| Multi-speaker or cross-clip range | Fail |
| 429 | Hold and poll |
| `LipSyncGenerationError` | `dismiss_failed`. Offer `fresh_lip_sync` |
| Timeout | Dismiss. Leave the original picture |

Jump-cut smooth (`smooth-jump-cuts`) stays an edit action. After it changes timing, the operator may run this POST. Do not fold it into the payload.
