# Descript: Video Regenerate

Public web client, build `react19/9a29d61183bce669600a9dd9a1f8588d708becac` (2026-10-19). Chunk **88** `88.fc0ea62a7f115f3adca9.js`.

## What it is

**Video Regenerate is lip-sync imputation of an existing talking-head section. It is not generative video-from-a-prompt.**

The cloud artifact whose `displayName` is the string `Video Regenerate` is (**static-bundle**, offset ~2054622):

| Field | Value |
| --- | --- |
| name | `imputation_lip_sync` |
| endpoint | `lip_sync` |
| variant | `"imputation"` |
| artifactType | `imputation_lip_sync` |
| type | `artifact` |
| surface | `LipsyncModel` |
| inputArtifactType | `original` |
| validTypes | `["audio"]` |
| displayInSuperToast | `false` |

`validTypes: ["audio"]` means the task is keyed off the **audio artifact of the edit**, not off a text prompt. The POST also sends `to_be_replaced_urls` for the picture span being replaced. The result is `{asset_id, output_artifact_id}` mapped to `{assetId, artifactIds: [output_artifact_id]}`.

The server model that paints the mouth is not in the client (**unknown**). The client's job is to build this payload, poll, and apply the output artifact.

## Three different products

| | Video Regenerate | Translate / dub lip-sync | Generate video |
| --- | --- | --- | --- |
| Bundle name | `imputation_lip_sync` | `translation_lip_sync` | kebab `GenerateVideo` |
| displayName | `Video Regenerate` | `lip-sync` | (generative action, not this task) |
| Endpoint | `POST /projects/{id}/lip_sync` | **same** path | not `lip_sync` |
| variant | `imputation` | `translation` | none on this task |
| Time range field | `additionalData.imputationAudioTimeRange` | `additionalData.dubAudioTimeRange` | — |
| prefix / suffix | `prefixUrls`, `suffixUrls` | forced to `[]` | — |
| Action symbols | `APPLY_LIP_SYNC`, `FRESH_LIP_SYNC` | `GENERATE_TRANSLATION_LIP_SYNC` | `generate-video` sits in the generative action set with `generate-image`, `generate-music`, `generate-sfx`, `youtube-thumbnail` |
| Credit key | `lip_sync` → `ai_media_generation`. Separate key `ai_regenerate_video` → `ai_media_generation` | `dubbing` → `ai_speech`, and `translation` → `translation` | `ai_gen_video` → `ai_media_generation` |

Same endpoint, two variants (**static-bundle**, translation spec at offset ~2056894). Generate video is a different kebab and is out of this spec.

`ai_regenerate_audio` → `ai_speech` is the **audio** regenerate credit, not the picture task. A wording change can spend speech credits to produce `audio_artifact_id`, then media-generation credits when variant `imputation` runs. Do not bill both from one key.

## Imputation payload

`payloadJsonFromPayload` requires `additionalData` or it throws `"additionalData is required for lip sync"` (surface `AITools`).

```text
POST /projects/{projectId}/lip_sync
{
  asset_id,                                      # video asset
  audio_artifact_id,                             # new or smoothed speech
  audio_artifact_time_range,                     # imputationAudioTimeRange
  prefix_urls,                                   # prefixUrls
  suffix_urls,                                   # suffixUrls
  to_be_replaced_urls,                           # toBeReplacedUrls
  variant: "imputation",
  composition_id                                 # compositionId
}
```

Translation sends the same keys with `variant: "translation"`, `prefix_urls: []`, `suffix_urls: []`, and the time range taken from `dubAudioTimeRange`.

Prefix and suffix URL lists are **inferred** to be temporal context around the replaced span (the names are static-bundle; the server's use of them is not described in the client).

## Orchestration symbols (static-bundle)

| Symbol | Role we will honor |
| --- | --- |
| `APPLY_LIP_SYNC` | Apply the output artifact |
| `FRESH_LIP_SYNC` | Run generation again |
| `LIP_SYNC_SEGMENTS` | The section is segmented |
| `DISMISS_FAILED_LIP_SYNC` (family) | Dismiss a failed segment |
| `HIDE_REGENERATE_LIP_SYNC_CONFIRMATION_MODAL` | A confirmation modal exists and can be suppressed |
| `LipsyncMode`, `LipsyncModel` | Mode and model surfaces |
| `LipSyncGenerationError`, `LipSyncGenerationErrorType` | Error types. Members not in this slice |
| `EditBoundaryRegenerationHelpers` | Edit-boundary helpers. Bodies not in this slice |

`SmoothJumpCuts` / kebab `smooth-jump-cuts` is a **different** action. Its credit key `smooth_jump_cuts` maps to `ai_editing`, not to `lip_sync`. Jump-cut healing can be what leads a user into Video Regenerate; it is not this POST.

The confirmation modal's body was not recovered. Help pages describe a visual-performance consent step (**static-help**). The bundle evidence for a gate is the modal symbol, not that help paragraph. Voice consent for a cloned speaker is a separate record: [../pseudocode/voice-consent.md](../pseudocode/voice-consent.md).

## What this pass did not recover

- Tensor layout, identity loss, or a lip-sync score threshold. Any quality gate in the Polish Clips spec is **inferred**, not a copied Descript scorer.
- A mode enum named `audio_only` / `audio_and_video`. Those labels are older help wording (**static-help**). The bundle split is "do not POST `lip_sync`" versus "POST variant `imputation`".
- Max selection length and a language lock. Not in this entry set. Do not copy a 250-character help limit into the contract.

Build spec: [../pseudocode/video-regenerate.md](../pseudocode/video-regenerate.md).
