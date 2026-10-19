# Feature inventory

Scope lock for Polish Clips. Each row is a behaviour we intend to build, mapped to the Descript API where the OpenAPI (version 1.2, 2026-10-19) has an operation. "Observed cost" stays empty until a test-Drive token probe.

Evidence: the public OpenAPI column is **static**. Editor project routes, HD ids, and credit categories are **static-bundle** or **decompiled** from web client build `react19/9a29d61183bce669600a9dd9a1f8588d708becac` (2026-10-19). See [api-notes.md](api-notes.md). "Observed cost" stays empty until a live account records a number. Studio Sound's cloud switch is the model enum `auto` | `v1` | `v3_5`, not an OpenAPI intensity field.

## Pipeline

| Feature | When | Input | Output | Where it runs | API | Open stack | Observed cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Import + transcribe | required | Local file or URL, language hint | Project or local media id; word timings | Server via API, or on-device ASR | `POST /jobs/import/project_media` then poll. Transcription is part of import (static). No word-JSON endpoint | ffmpeg decode + Whisper-class ASR with word timestamps | |
| Filler removal | required | Transcript words | Same words with `ignored=true` on fillers | Local model. API path is a prompt | `POST /jobs/agent` prompt. Official example text is "remove all filler words" (static). Ignore/strikethrough is not a field | Lexicon + context filter; set ignore, do not delete the word | |
| Retake removal | required | Transcript utterances | Earlier takes marked ignored | Local model, or one agent prompt | Prompt only. No retake schema | Near-duplicate utterance match; keep the last take | |
| Studio Sound–class enhance | required | Speech audio | Enhanced audio, original kept | Local denoiser, or `POST /projects/{id}/speech_enhancement` | Public API: prompt only, no version field (**static**). Web client: `{audio_asset_id, audio_artifact_id, version?}` with model `auto` \| `v1` \| `v3_5` (**static-bundle**) | RNNoise-class or DeepFilterNet-class; ffmpeg `afftdn` as a weak baseline. See [pseudocode/studio-sound.md](pseudocode/studio-sound.md) | |
| Captions (cues) | required | Non-ignored words | SRT, VTT, and `Cue[]` with word spans | Local grouper | Agent prompt "add captions". `POST /export/transcript` `format: srt` is a file, not a style (static) | [pseudocode/captions.md](pseudocode/captions.md) | |
| Caption style | required | `CaptionStyle` | Preview and saved style | Local only | No caption-style schema (static). Underlord's look is uncontrolled | [pseudocode/caption-style.md](pseudocode/caption-style.md) | |
| Caption burn-in | secondary | Video + `Cue[]` + style | Video file with text in the frames | Local render. Off unless asked | None. A publish job may burn Underlord's own captions; that style is not ours | [pseudocode/caption-burnin.md](pseudocode/caption-burnin.md) | |
| Clip cut | required | Word or time selection | New clip of kept ranges inside the selection | Local ffmpeg trim/concat, or a coarse agent prompt | Prompt only ("create a 30-second highlight reel" is the spec example) | Selection → kept ranges → encode | |
| Publish / export | secondary | Composition or local master | File, or share URL + download URL | API publish job, or local encode | `POST /jobs/publish`; `GET /projects/{id}` lists existing `publishes` | [pseudocode/editor/export-render.md](pseudocode/editor/export-render.md) | |

## Editor foundation

The editor is specified under [pseudocode/editor/](pseudocode/editor/). It is the canvas the polish pipeline seeds. It is not a Descript clone. None of these rows have an OpenAPI operation (static).

| Feature | When | Spec |
| --- | --- | --- |
| Project, one composition, video / audio / caption tracks | Required with the editor | [pseudocode/editor/overview.md](pseudocode/editor/overview.md), [timeline-model.md](pseudocode/editor/timeline-model.md) |
| Transcript-linked ignore, ripple / roll / slip | Required with the editor | [pseudocode/editor/selection-and-edits.md](pseudocode/editor/selection-and-edits.md) |
| Preview, transcript panel, timeline, inspector | Required with the editor | [pseudocode/editor/ui-surface.md](pseudocode/editor/ui-surface.md) |
| Per-clip gain, mute, pan, fades, highpass / lowpass | Required with the editor | [pseudocode/editor/audio-mixer.md](pseudocode/editor/audio-mixer.md) |
| Studio Sound as a clip effect node | Required with the editor; same engines as the pipeline stage | [pseudocode/studio-sound.md](pseudocode/studio-sound.md) |
| Media transform, crop, opacity, caption layer | Required with the editor | [pseudocode/editor/layers.md](pseudocode/editor/layers.md) |
| Offline render + optional burn-in | Required once export ships; burn-in stays optional per export | [pseudocode/editor/export-render.md](pseudocode/editor/export-render.md) |
| Text overlays that reuse caption fonts | Later, types are in the layer spec | [pseudocode/editor/layers.md](pseudocode/editor/layers.md) |
| Shapes, blend modes other than normal | Later | [pseudocode/editor/layers.md](pseudocode/editor/layers.md) |
| Image, video, and GIF overlays | Required with the editor | [pseudocode/editor/overlays.md](pseudocode/editor/overlays.md) |
| Stock / GIF search providers | Interface now; live keys later | [pseudocode/editor/stock-asset-providers.md](pseudocode/editor/stock-asset-providers.md) |
| Voiceover record, import, punch-in | Required with the editor | [pseudocode/editor/voiceover.md](pseudocode/editor/voiceover.md) |
| Duck voiceover under dialogue | Optional flag. Other music ducking stays later | [pseudocode/editor/audio-mixer.md](pseudocode/editor/audio-mixer.md) |
| Self-record with background removed | In scope after the overlay track. Not part of the polish-only pipeline. Writes the shared `background_mask` | [pseudocode/editor/self-record-bg-remove.md](pseudocode/editor/self-record-bg-remove.md), [pseudocode/green-screen.md](pseudocode/green-screen.md) |
| Ordered visual effects on a layer | Later. Empty list in the MVP | [pseudocode/visual-effects-model.md](pseudocode/visual-effects-model.md) |
| Align two clips by waveform | In scope for multicam. Not part of the single-camera polish | [pseudocode/editor/audio-waveform-align.md](pseudocode/editor/audio-waveform-align.md) |
| Peak EQ bands | Later; stored and bypassed | [pseudocode/editor/audio-mixer.md](pseudocode/editor/audio-mixer.md) |
| Nested sequences, scene export, NLE XML | Later | [pseudocode/editor/timeline-model.md](pseudocode/editor/timeline-model.md) |

A polish-only build can ship before the full editor: cues, style preview, and optional burn-in do not wait on shapes or ducking. The editor specs are still in scope for the product, not parked as out of scope.

## AI features from the web client

None of these are staging OpenAPI operations (**static**). The web app posts them to `https://api.descript.com/projects/{id}/...` or runs them as kebab actions (**static-bundle**). They are later than the polish pipeline. They are specified.

| Topic | Bundle name | When | Docs |
| --- | --- | --- | --- |
| Eye contact | `com.descript.eyeContact`, `POST .../eye_gaze_correction`, artifact `eye_contact`. No UI params. 10 AI credits per use. Flag `eyeContactRequested` | Later. Not a pipeline stage | [descript-analysis/eye-contact.md](descript-analysis/eye-contact.md), [pseudocode/eye-contact.md](pseudocode/eye-contact.md) |
| Green Screen | `com.descript.backgroundRemoval`, shared `POST .../background_removal` → `background_mask`. 10 AI credits per use | Later. Self-record can fill the mask locally | [pseudocode/green-screen.md](pseudocode/green-screen.md) |
| Blur speaker background | `com.descript.backgroundBlur`, Amount default `0.5`. Same mask. 10 AI credits on the mask task | Later | [pseudocode/blur-speaker-background.md](pseudocode/blur-speaker-background.md) |
| Portrait Lighting | `com.descript.portraitLighting`, default `[1, 0.58, 0.38, 0.05, -0.05, 0.15, 0]`. Warn if stacked with Uplight | Later | [pseudocode/portrait-lighting.md](pseudocode/portrait-lighting.md) |
| Uplighting | `com.descript.uplighting`, default `[1, 0.65, 0.65, 0.05, -0.05, 0]`. No blur slot | Later | [pseudocode/uplighting.md](pseudocode/uplighting.md) |
| Chroma key | `com.descript.chromakey`. Local. Default key RGB `(0, 255, 74)`, similarity `0.4`, smoothness `0.08`, spill `0.1` | Later | [pseudocode/chroma-key.md](pseudocode/chroma-key.md) |
| Color adjustments | `com.descript.colorAdjustments`. Local. 10-param vector, TemperatureMode default `1` | Later | [pseudocode/color-adjustments.md](pseudocode/color-adjustments.md) |
| Center active speaker | `com.descript.speakerFocus`, `POST .../face_tracking`. Fails over 1.5 hours, no faces, or bad format | Later | [pseudocode/center-active-speaker.md](pseudocode/center-active-speaker.md) |
| Enhance suite | No `EnhanceVideo` enum. Orchestrates the rows above | Later | [descript-analysis/enhance-video-suite.md](descript-analysis/enhance-video-suite.md), [pseudocode/enhance-video-suite.md](pseudocode/enhance-video-suite.md) |
| Skin smoothing | Flag `beautifyRequested`. Module 351916 vector. 5 AI credits per file on first apply. Not an HD id | Later | [descript-analysis/skin-smoothing.md](descript-analysis/skin-smoothing.md), [pseudocode/skin-smoothing.md](pseudocode/skin-smoothing.md) |
| Studio Sound | `POST .../speech_enhancement`, artifact `speech_enhanced`, model `auto` \| `v1` \| `v3_5` | Required as a local denoiser. Cloud path is optional | [pseudocode/studio-sound.md](pseudocode/studio-sound.md) |
| Video Regenerate | `imputation_lip_sync`, `POST .../lip_sync` variant `imputation`. Not `generate-video` | Later. Voice consent when the audio is synthetic, plus a visual confirmation | [descript-analysis/video-regenerate.md](descript-analysis/video-regenerate.md), [pseudocode/video-regenerate.md](pseudocode/video-regenerate.md) |
| Publish AI | `suggest-title`, `youtube-description-v2`, `show-notes-v2`, skill `prepare-for-publish`. Category `ai_writing` | Later. Does not export | [descript-analysis/youtube-publish-ai.md](descript-analysis/youtube-publish-ai.md), [pseudocode/youtube-titles-descriptions.md](pseudocode/youtube-titles-descriptions.md) |
| Remove an object | Edit with AI, **image layers only**. Not tied to an HD id in this pass | Later. Video path stays off by default | [descript-analysis/object-removal.md](descript-analysis/object-removal.md), [pseudocode/object-removal.md](pseudocode/object-removal.md) |
| Voice that sounds like the speaker | Custom AI Speaker, then audio regenerate. Picture step is imputation, not a new generator | Later, and only with [pseudocode/voice-consent.md](pseudocode/voice-consent.md). Punch-in is the default fix | [descript-analysis/voice-clone.md](descript-analysis/voice-clone.md) |

## Later / out

Translate / dub stays out of the default build. Its picture step is the same `lip_sync` endpoint with `variant: "translation"` and empty prefix/suffix URL lists, specified only so Video Regenerate is not confused with it. Kebab `generate-video` is a generative action and is out. Rooms, comments, Drive collaboration, Brand Studio, and layout packs stay out. Stylize filters (film grain, VHS, ascii, vignette, and the other allowlist ids in the enhance analysis) are a later catalog, not the Look Good suite.

Green Screen on arbitrary footage is the shared mask spec, later, not a second matte format. `GET /search` and `POST /edit_in_descript/schema` exist (**static** OpenAPI) and are unused. Premiere / FCPXML interchange is later, beside NLE XML, and is not part of the MVP render.

## Fixtures

Create these outside git (a path matched by `.gitignore`, such as `captures/fixtures/`):

| Id | Contents | Used to check |
| --- | --- | --- |
| `clean` | Short, quiet, scripted speech, no fillers | Transcript timings, caption cue breaks, no false filler hits |
| `fillers-retakes` | Same sentence attempted twice, with "um" / "uh" and one false start | Ignore flags, last-take kept, strikethrough restore |
| `noisy` | Same script with room noise or a fan | Enhance loudness and noise floor; captions still align |

Record wall-clock time and, for API runs, `media_seconds_used` and `ai_credits_used`.

## Suggested probe order

1. Import `clean` with a direct upload (`content_type` + `file_size`).
2. Read `GET /projects/{project_id}` and store `compositions[0].id`.
3. One agent job whose prompt asks for filler ignore, Studio Sound, and captions together. See [pseudocode/underlord-agent-job.md](pseudocode/underlord-agent-job.md).
4. `POST /export/transcript` as `srt` and as `txt`. Diff against the source script.
5. Publish is optional and spends render time; skip it until the transcript diff is understood.
