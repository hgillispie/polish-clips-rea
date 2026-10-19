# Studio Sound

Cloud speech enhancement plus a local denoiser of the same class. The product name is Descript's. The endpoint and payload are from the web client, not from the public OpenAPI.

Build `react19/9a29d61183bce669600a9dd9a1f8588d708becac`. Spec offset ~2056172 in chunk 88. Effect id string `com.descript.studioSound` (**static-bundle**). The OpenAPI has no Studio Sound field (**static**).

## Cloud task (static-bundle)

```text
name:                 studio_sound
displayName:          "Studio Sound"
endpoint:             speech_enhancement
artifactType:         speech_enhanced
inputArtifactType:    original
type:                 blocking
validTypes:           [audio]
surface:              StudioSound
displayInSuperToast:  false
trackedFeatureId:     aiEffectStudioSound
upgradeOrigin:        GenerateStudioSound     # kebab generate-studio-sound

Model enum (recovered):
  auto = "auto"
  v1   = "v1"
  v3_5 = "v3_5"

POST /projects/{projectId}/speech_enhancement
  audio_asset_id:     asset id
  audio_artifact_id:  artifact id
  version:            omitted when studioSoundModel is "auto", otherwise "v1" or "v3_5"

Result JSON:
  speech_enhancement_audio_asset_id
  speech_enhancement_audio_artifact_id
Mapped to { assetId, artifactIds: [speech_enhancement_audio_artifact_id] }.
```

`payloadJsonFromPayload` reads `additionalData.studioSoundModel`. If that value is `auto`, the JSON `version` key is absent, not the string `"auto"`.

Media flags (**static-bundle**): `speechEnhanceEnabled`, `studioSoundIntensity`. Intensity is on the audio ref. It is **not** a field of this POST. Do not send `low` / `medium` / `high` as `version`. What `studioSoundIntensity` scales is **unknown**. The local effect node still has its own strength enum; that enum is ours.

Credit key `studio_sound` → `ai_effects`. Integer cost was not in the visual-effect credit sentences. Paywall string `PreSeason6EyeContactGreenScreenStudioSoundPaywallBehavior` includes Studio Sound. Kebab `generate-studio-sound`.

Poll is the shared helper in [visual-effects-model.md](visual-effects-model.md): 429 → `{id, state: "hold"}`.

## Cloud steps

```text
function enhance_cloud(project_id, media, model) -> artifact:
  if media.kind != "audio" and not media.has_audio:
    fail "speech_enhancement validTypes is audio"
  if model not in ("auto", "v1", "v3_5"):
    fail "studio sound model"
  media.speechEnhanceEnabled = true
  task = post_cloud_effect(auth, project_id, SPECS.studio_sound, {
    assetId: media.asset_id,
    artifactId: media.audio_artifact_id,
    additionalData: { studioSoundModel: model }
  })
  task = wait_cloud_effect(...)
  enhanced = task.result
  if enhanced.assetId is null:
    fail "no speech_enhancement_audio_asset_id"
  # Durations must match the source within 50 ms or the clip stays on the original.
  return enhanced
```

Playback uses the enhanced **audio** asset and the original **video**, same as the local path. The cloud result replaces the audio artifact id. It does not rewrite transcript times.

`version` omitted vs `v1` vs `v3_5` is the only server switch this slice shows. Default the call to `auto`.

## Local algorithm

Use this when there is no Descript session. Keep the source file. Switch the enhanced asset on at playback and export.

```text
input:
  asset            MediaAsset
  options
    backend        "deepfilter" | "rnnoise" | "ffmpeg_afftdn" | "speech_enhancement"
    strength       "low" | "medium" | "high"     # local backends only
    model          "auto" | "v1" | "v3_5"        # speech_enhancement only, default auto
    project_id     string | null
output:
  enhanced         MediaAsset
  report
    backend        string
    version        string | null
    peak_dbfs      number | null
    credits_key    "studio_sound" | null
```

```text
function enhance(asset, options) -> (enhanced, report):
  if options.backend == "speech_enhancement":
    artifact = enhance_cloud(options.project_id, asset, options.model)
    return artifact_as_media(artifact), report(backend="speech_enhancement", version=options.model, credits_key="studio_sound")

  wav = ffmpeg_decode(asset.path, sample_rate=48000, channels=1, format="wav")
  if options.backend == "ffmpeg_afftdn":
    out = ffmpeg_afftdn(wav, strength_to_nr(options.strength))
  else if options.backend == "rnnoise":
    out = rnnoise_denoise(wav)
  else if options.backend == "deepfilter":
    out = deepfilternet(wav, strength=options.strength)
  else:
    fail "unknown backend"

  out = loudness_normalize(out, target_lufs=-16, true_peak_dbfs=-1.5)
  peak = measure_peak_dbfs(out)
  if peak > -0.1:
    fail "limiter failed; refuse to write a clipped master"
  return write_wav(out), report(backend=options.backend, peak_dbfs=peak, credits_key=null)

function strength_to_nr(strength) -> number:
  # ffmpeg afftdn noise reduction in dB. Local fallback only.
  return { low: 6, medium: 12, high: 20 }[strength]
```

Default local backend: `deepfilter` if the model file exists, else `rnnoise`, else `ffmpeg_afftdn`.

The mixer effect node in [editor/audio-mixer.md](editor/audio-mixer.md) calls this local `enhance`. Its `strength` field is the local enum. Do not map that enum onto `v1` / `v3_5`.

## Public agent prompt

`POST /v1/jobs/agent` can still be asked, as prose, to add Studio Sound. That host has no `version` field (**static** OpenAPI). The sentence "medium intensity" is a request, not `studioSoundIntensity`. Prefer `speech_enhancement` when the operator is driving the web API with a session, and the local backends otherwise. The agent job remains in [underlord-agent-job.md](underlord-agent-job.md) for the documented public API.

Kebab `generate-studio-sound` is the in-app action id, separate from both.

## Errors

| Case | Behaviour |
| --- | --- |
| Decode failure | Stop the local stage. The rest of the pipeline can continue on the original |
| Model file missing | Fall back `deepfilter` → `rnnoise` → `ffmpeg_afftdn`. Record `report.backend` |
| Output duration mismatch > 50 ms | Discard the enhanced audio. Leave `speechEnhanceEnabled` false |
| `model` not in auto / v1 / v3_5 | Fail before POST |
| 429 on poll | Hold |
| Payment error | Stop. Do not retry |
| Public agent `project_changed: false` | HTTP job succeeded and the effect did not run |

## Build options

| Option | When |
| --- | --- |
| `deepfilter` / `rnnoise` / `afftdn` | Default. No Descript credits |
| `POST .../speech_enhancement` | Operator session on `api.descript.com`. Model `auto` by default |
| Underlord prompt on `descriptapi.com` | Black box. No version field |
