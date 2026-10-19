# Descript: Eye Contact

Public web client, build `react19/9a29d61183bce669600a9dd9a1f8588d708becac` (2026-10-19). Chunk **88** is `88.fc0ea62a7f115f3adca9.js`. Wakaru modules are cited by id. Recovered JavaScript is not in this repo.

Eye Contact is a cloud artifact on a video, then a parameter-less effect. It is not skin smoothing and it is not Video Regenerate.

## Symbols

| Item | Value | Tag |
| --- | --- | --- |
| HD id | `HD.EYE_CONTACT` = `com.descript.eyeContact` | static-bundle, chunk 88 ~3772069 |
| Task name | `eye_contact` | static-bundle, offset ~2054012 |
| displayName | `Eye Contact` | static-bundle |
| Endpoint | `eye_gaze_correction` on `https://api.descript.com` | static-bundle. `descriptapi.com` does not appear in chunk 88 |
| artifactType | `eye_contact` | static-bundle |
| inputArtifactType | `original` | static-bundle |
| type | `artifact` | static-bundle |
| isMtsOnlyEffect | `true` | static-bundle |
| validTypes | `["video"]` | static-bundle |
| Media flag | `video.eyeContactRequested` | static-bundle |
| UI descriptor | Wakaru `module-35972`: `parameters: []`, `defaultPreset: []`, category Media | decompiled |
| ID binding | Wakaru `module-514277` binds `HD.EYE_CONTACT` | decompiled |
| Help URL embedded in the descriptor | `https://help.descript.com/effects-animations-transitions/eye-contact` | static-help |
| upgradeOrigin | `GenerateEyeContact`, kebab `generate-eye-contact` | static-bundle |
| trackedFeatureId | `aiEffectEyeContact` | static-bundle |
| surface | `EyeContact` | static-bundle |
| Agent field | `eyeContact` boolean | static-bundle |
| Credits | 10 AI credits per use; category key `eye_contact` → `ai_effects` | static-bundle |
| Paywall flag string | `PreSeason6EyeContactGreenScreenStudioSoundPaywallBehavior` | static-bundle |
| Eligibility | `isEligibleMediaRef` (minified `n.kx`). Body not recovered | static-bundle symbol, body unknown |

## What the client does

1. Enabling the effect on a video media ref sets `eyeContactRequested` (**static-bundle**).
2. The scheduler enqueues cloud task `eye_contact`.
3. `POST /projects/{projectId}/eye_gaze_correction` with `{asset_id}` from `payloadJsonFromPayload` (**static-bundle**).
4. Poll `GET /projects/{projectId}/eye_gaze_correction/{taskId}`. HTTP 429 is turned into `{id, state: "hold"}` by the shared helper (module factory at offset ~2054622, function pair `mA` / `OZ`).
5. `resultFromResultJson` maps `{asset_id, artifact_ids}` to `{assetId, artifactIds}`. Note the plural `artifact_ids`. Background removal uses a singular `output_artifact_id` instead.
6. Render attaches effect type `com.descript.eyeContact`. The UI descriptor has no strength, no region, and no other parameter (**decompiled**).

`inputArtifactType: "original"` means the job reads the original asset, not a previous effect's output (**static-bundle**). Gaze correction is not baked into the background-mask artifact. The local renderer stacks it with other effects.

No landmark model, WASM, or gaze weights sit in the public entry chunks (**static-bundle**). Superpowered and rnnoise WASM paths in the corpus are unrelated. Inference is server-side.

Agent copy: async cloud effect, 10 AI credits per use, requires a speaker associated with the video (**static-bundle**). The same 10-credit sentence is shared with other cloud visual effects. `isEligibleMediaRef`'s exact predicate is **unknown**. A speaker requirement is the agent string, not a traced branch.

## API split

Staging OpenAPI 1.2 on `descriptapi.com/v1` has no eye-contact operation (**static** OpenAPI). The web app does not call that host for this effect. `POST /v1/jobs/agent` can only ask in prose. The structured path is the project route above.

Build spec: [../pseudocode/eye-contact.md](../pseudocode/eye-contact.md). Effect graph: [../pseudocode/visual-effects-model.md](../pseudocode/visual-effects-model.md).
