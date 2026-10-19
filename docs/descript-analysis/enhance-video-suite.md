# Descript: Look Good / enhance video suite

Public web client, build `react19/9a29d61183bce669600a9dd9a1f8588d708becac` (2026-10-19). There is no enum member named `EnhanceVideo`. The Features-menu bucket is the Look Good / media visual effects below.

Chunk **88** is `88.fc0ea62a7f115f3adca9.js`. Wakaru ids are from the 2026-10-19 unpack of chunks 1445, 1356, and 8630. Recovered JavaScript is not in this repo.

## Shared mask task

Portrait Lighting, Uplighting, Blur speaker background, and Green Screen do not each POST a different matting URL. One cloud task feeds all four (**static-bundle**, offset ~2049550):

| Field | Value |
| --- | --- |
| endpoint | `background_removal` |
| name | `background_mask` |
| displayName | `background effect (removal or blur)` |
| artifactType | `background_mask` |
| inputArtifactType | `original` |
| type | `blocking` |
| isMtsOnlyEffect | `true` |
| validTypes | `image`, `video`, `avatar` |
| effectTypes | `HD.BACKGROUND_BLUR`, `HD.BACKGROUND_REMOVAL`, `HD.UPLIGHTING`, `HD.PORTRAIT_LIGHTING` |
| POST body | `{asset_id}` |
| Result JSON | `{asset_id, output_artifact_id}` mapped to `{assetId, artifactIds: [output_artifact_id]}` |
| upgradeOrigin | `GenerateBackgroundMask` |
| trackedFeatureId | `aiEffectGreenScreen` |
| surface | `BackgroundRemoval` |

The client then runs local GPU shaders with that mask (**decompiled** Wakaru modules). Server matting weights are not in the client.

Media flags (**static-bundle**): `backgroundMaskRequested`, `portraitLightingRequested`, `uplightingRequested`. Eye Contact is a different endpoint (`eye_gaze_correction`). Center active speaker is `face_tracking`. Skin smoothing is `beautifyRequested` and is not in this task's `effectTypes`.

## HD ids

**static-bundle**, chunk 88 ~3772069:

| Enum | Wire string |
| --- | --- |
| `BACKGROUND_BLUR` | `com.descript.backgroundBlur` |
| `BACKGROUND_REMOVAL` | `com.descript.backgroundRemoval` |
| `UPLIGHTING` | `com.descript.uplighting` |
| `PORTRAIT_LIGHTING` | `com.descript.portraitLighting` |
| `EYE_CONTACT` | `com.descript.eyeContact` |
| `CENTER_ACTIVE_SPEAKER` | `com.descript.speakerFocus` |

Also present as string constants, not in that six-member enum: `com.descript.glassBlur`, `com.descript.checkerboardMask`, `com.descript.glow`. Chroma key and color adjustments use their own ids (`com.descript.chromakey`, `com.descript.colorAdjustments`) on the effect-merge allowlist.

## Per-effect facts

### Portrait Lighting — decompiled `module-107643`, `module-379791`

- Id `com.descript.portraitLighting`.
- Visible parameters: Strength, Foreground Brightness, Background Brightness.
- Hidden parameters: foreground warmth, background warmth, background blur, mask feather.
- Default vector `[1, 0.58, 0.38, 0.05, -0.05, 0.15, 0]`.
- Render: optional directional blur of the mask with radius `10 ** (blur * log10(200))`, then lighting shader (minified name `K`) using strength and the foreground/background brightness and warmth.
- Agent schema accepts `{strength?, foregroundBrightness?, backgroundBrightness?}` or `true`. Defaults strength `1`, foreground brightness `0.58`, background brightness `0.38`. Boolean `true` becomes the full 7-vector (**static-bundle**).
- Agent copy: async cloud effect, costs AI credits per use, requires a speaker. The integer is **not** in that string. Tracked feature `aiEffectLighting`.

### Uplighting — decompiled `module-985267`, `module-308039`

- Id `com.descript.uplighting`.
- Visible: Strength, Foreground Brightness, Background Brightness.
- Hidden: foreground warmth, background warmth, mask feather. There is **no** background-blur slot (the portrait vector is longer by one).
- Default vector `[1, 0.65, 0.65, 0.05, -0.05, 0]`.
- Same lighting shader, no pre-blur pass.
- Agent defaults: strength `1`, foreground `0.65`, background `0.65`. Boolean `true` becomes that 6-vector.
- Flag `uplightingRequested`. Same "AI credits per use" sentence, no integer.

### Blur speaker background — static-bundle, chunk 88 ~4893291

- UI name `blur speaker background`.
- Id `HD.BACKGROUND_BLUR`.
- One parameter, `Amount`. `defaultPreset: [0.5]`.
- Help URL embedded: `https://help.descript.com/effects-animations-transitions/blur-speaker-background` (**static-help**).
- Uses `background_mask`. Agent: 10 AI credits per use, needs a speaker. Credit key `background_blur` → `ai_effects`.

### Green Screen — decompiled `module-419488`

- UI name `green screen`. Id `HD.BACKGROUND_REMOVAL`. No parameters (toggle).
- Shader name `BackgroundRemoval`. It multiplies content by `mask.r * mask.a`.
- Same `background_removal` POST. Agent: 10 AI credits per use. Credit key `green_screen` → `ai_effects`.
- Agent copy prefers `chromaKey` when the backdrop is a solid color. Chroma key is a different, local effect.

### Chroma key — decompiled `module-514462` plus the UI descriptor

- UI name `chroma key`, category Color.
- Parameters: key red, key green, key blue, Similarity, Smoothness, Spill.
- Default UI key about RGB `(0, 255, 74)`, similarity `0.4`, smoothness `0.08`, spill `0.1`. Stored slots for the key are `fromUiValue` encodings, not raw 0–255 bytes.
- Shader: distance in UV, alpha `pow(clamp((dist - similarity) / smoothness), 1.5)`, then spill desaturation.
- Not in the cloud property subset. Local GPU. No `background_removal` POST.

### Color adjustments — decompiled `module-88922`

- Parameter index order (`ft`): Exposure, Contrast, Highlights, Shadows, BlackPoint, Saturation, Vibrancy, Temperature, Tint, TemperatureMode.
- TemperatureMode values named `Helland` and `Linear`. Default vector is zeros except TemperatureMode `1`. Which name is `1` is **unknown** (the evidence summary does not pair them).
- Not in the cloud subset. Treated as a free local grade (**inferred** from that absence and from sibling free-GPU copy on invert).

### Center active speaker — decompiled `module-916791`, `module-284685`

- Id `com.descript.speakerFocus`. UI `parameters: []`.
- Cloud task name `center_active_speaker`, endpoint `face_tracking`, artifactType `face_tracking`, type `artifact`, validTypes `video`, `displayInSuperToast: false`.
- POST `{asset_id}`. Result uses singular `output_artifact_id`.
- Flag `speakerFocusRequested`. trackedFeatureId `aiEffectCenterActiveSpeaker`. upgradeOrigin `CenterActiveSpeaker`.
- Failure reasons (**static-bundle**): `face-detection:no-faces`, `video:max-duration-exceeded` (copy: longer than 1.5 hours), `video:unsupported-format`.
- Kebab ids `center-active-speaker` and `center-active-speaker-v2`. The v2 delta is **unknown**.
- Schema symbol `ActiveSpeakerFramesEncodedSchema` appears in chunks 760 and 1356. Field list **unknown**.
- Credit key `center_active_speaker` → `ai_effects`. A second key `center_active_speaker_underlord` maps to `["ai_effects", "ai_agent"]`. No "10 credits" integer was on this task's string.

### Skin smoothing

Separate from this mask. See [skin-smoothing.md](skin-smoothing.md). Flag `beautifyRequested`. 5 AI credits per file on first apply. Not one of the six `HD` ids above.

### Eye Contact

Separate endpoint. See [eye-contact.md](eye-contact.md). 10 AI credits per use.

## Stacking Portrait and Uplight

The agent schema is one object with both `portraitLighting` and `uplighting` optional. Nothing in the recovered schema rejects the pair (**static-bundle** absence). Help text says stacking them looks uneven (**static-help**). Polish Clips warns and asks before applying both. See [../pseudocode/enhance-video-suite.md](../pseudocode/enhance-video-suite.md).

## What is local vs cloud

Agent visual property list `Ba` (**static-bundle**) includes pixelate, film grain, chroma key, color adjustments, zoom blur, blur, background blur, background removal, eye contact, skin smoothing, vignette, portrait lighting, uplighting, invert, threshold, color tone, infrared, selective color, VHS, ascii.

Cloud subset `Qa`: background blur, background removal, eye contact, center active speaker, portrait lighting, uplighting.

Invert is described as a free GPU effect. Infrared and threshold are free GPU effects in the same schema. Chroma key and color adjustments are absent from `Qa`.

## Stylize, later

These ids are on the effect-merge allowlist and are not part of the Look Good suite this spec implements: `glfx.triangleBlur`, `com.descript.filmGrain`, `com.descript.invert`, `com.descript.vignette`, `com.descript.threshold`, `com.descript.colorTone`, `com.descript.infrared`, `com.descript.selectiveColor`, `com.descript.vhs`, `com.descript.ascii`, `com.descript.pixelation`, `glfx.zoomBlur`, `com.descript.glassBlur`, `com.descript.checkerboardMask`, `com.descript.glow`. A later catalog can add them as local shaders. They do not POST `background_removal`.

## Specs

- Graph and flags: [../pseudocode/visual-effects-model.md](../pseudocode/visual-effects-model.md)
- Orchestrator: [../pseudocode/enhance-video-suite.md](../pseudocode/enhance-video-suite.md)
- [../pseudocode/portrait-lighting.md](../pseudocode/portrait-lighting.md), [../pseudocode/uplighting.md](../pseudocode/uplighting.md), [../pseudocode/blur-speaker-background.md](../pseudocode/blur-speaker-background.md), [../pseudocode/green-screen.md](../pseudocode/green-screen.md), [../pseudocode/chroma-key.md](../pseudocode/chroma-key.md), [../pseudocode/color-adjustments.md](../pseudocode/color-adjustments.md), [../pseudocode/center-active-speaker.md](../pseudocode/center-active-speaker.md)
- Self-record capture writes the same mask the green-screen shader reads: [../pseudocode/editor/self-record-bg-remove.md](../pseudocode/editor/self-record-bg-remove.md)
