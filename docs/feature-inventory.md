# Feature inventory

Scope lock for Polish Clips. Each row is a behaviour we intend to build, mapped to the Descript API where the OpenAPI (version 1.2, 2026-10-19) has an operation. "Observed cost" stays empty until a test-Drive token probe.

Evidence: API column is **static**. Product behaviour that the spec does not name (ignore versus hard delete, Studio Sound intensity, eye contact) is **inferred** from Descript's product language and is unverified against a live account.

## Pipeline

| Feature | When | Input | Output | Where it runs | API | Open stack | Observed cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Import + transcribe | required | Local file or URL, language hint | Project or local media id; word timings | Server via API, or on-device ASR | `POST /jobs/import/project_media` then poll. Transcription is part of import (static). No word-JSON endpoint | ffmpeg decode + Whisper-class ASR with word timestamps | |
| Filler removal | required | Transcript words | Same words with `ignored=true` on fillers | Local model. API path is a prompt | `POST /jobs/agent` prompt. Official example text is "remove all filler words" (static). Ignore/strikethrough is not a field | Lexicon + context filter; set ignore, do not delete the word | |
| Retake removal | required | Transcript utterances | Earlier takes marked ignored | Local model, or one agent prompt | Prompt only. No retake schema | Near-duplicate utterance match; keep the last take | |
| Studio Sound–class enhance | required | Speech audio | Enhanced audio, original kept | Local denoiser, or agent prompt | Prompt "add studio sound". No intensity parameter (static) | RNNoise-class or DeepFilterNet-class; ffmpeg `afftdn` as a weak baseline | |
| Captions (cues) | required | Non-ignored words | SRT, VTT, and `Cue[]` with word spans | Local grouper | Agent prompt "add captions". `POST /export/transcript` `format: srt` is a file, not a style (static) | [pseudocode/captions.md](pseudocode/captions.md) | |
| Caption style | required | `CaptionStyle` | Preview and saved style | Local only | No caption-style schema (static). Underlord's look is uncontrolled | [pseudocode/caption-style.md](pseudocode/caption-style.md) | |
| Caption burn-in | secondary | Video + `Cue[]` + style | Video file with text in the frames | Local render. Off unless asked | None. A publish job may burn Underlord's own captions; that style is not ours | [pseudocode/caption-burnin.md](pseudocode/caption-burnin.md) | |
| Clip cut | required | Word or time selection | New clip of kept ranges inside the selection | Local ffmpeg trim/concat, or a coarse agent prompt | Prompt only ("create a 30-second highlight reel" is the spec example) | Selection → kept ranges → encode | |
| Publish / export | secondary | Composition or local master | File, or share URL + download URL | API publish job, or local encode | `POST /jobs/publish`; `GET /projects/{id}` lists existing `publishes` | [pseudocode/editor/export-render.md](pseudocode/editor/export-render.md) | |

## Research note (non-blocking)

| Feature | MVP | What we know | What we will not do yet |
| --- | --- | --- | --- |
| Eye contact | no | Descript markets an eye-contact correction. The OpenAPI has no operation, schema field, or example prompt for it (static). It might be prompt-only or UI-only (**inferred**, unknown) | Do not add a pipeline stage. A later token probe can try one explicit prompt and record `project_changed` plus `agent_response`. Failure or a vague reply leaves the feature unknown |

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
| Self-record with background removed | In scope after the overlay track. Not part of the polish-only pipeline | [pseudocode/editor/self-record-bg-remove.md](pseudocode/editor/self-record-bg-remove.md) |
| Align two clips by waveform | In scope for multicam. Not part of the single-camera polish | [pseudocode/editor/audio-waveform-align.md](pseudocode/editor/audio-waveform-align.md) |
| Peak EQ bands | Later; stored and bypassed | [pseudocode/editor/audio-mixer.md](pseudocode/editor/audio-mixer.md) |
| Nested sequences, scene export, NLE XML | Later | [pseudocode/editor/timeline-model.md](pseudocode/editor/timeline-model.md) |

A polish-only build can ship before the full editor: cues, style preview, and optional burn-in do not wait on shapes or ducking. The editor specs are still in scope for the product, not parked as out of scope.

## AI features from public Descript docs

Help pages fetched 2026-10-19. None of these are OpenAPI operations (static). Build specs are local and clean-room.

| Topic | Descript’s name | When for Polish Clips | Docs |
| --- | --- | --- | --- |
| Appearance touch-up | Skin smoothing. Not Eye Contact | Later | [descript-analysis/skin-smoothing.md](descript-analysis/skin-smoothing.md), [pseudocode/skin-smoothing.md](pseudocode/skin-smoothing.md) |
| Remove an object | Edit with AI, **image layers only**. Video inpainting is not in the help snapshot | Later. Video path is explicitly off by default | [descript-analysis/object-removal.md](descript-analysis/object-removal.md), [pseudocode/object-removal.md](pseudocode/object-removal.md) |
| Voice that sounds like the speaker | Custom AI Speaker, then Regenerate. “Overdub” is the retired label | Later, and only with [pseudocode/voice-consent.md](pseudocode/voice-consent.md). Punch-in voiceover is the default fix | [descript-analysis/voice-clone.md](descript-analysis/voice-clone.md) |
| Eye contact | Eye Contact effect | Research note. Still not a pipeline stage | Help summary in the skin-smoothing analysis |

## Later / out

Translate / dub, Rooms, comments, Drive collaboration, Brand Studio, layout packs. A general green-screen effect on arbitrary footage is not a separate MVP; the self-record path has its own matte. `GET /search` and `POST /edit_in_descript/schema` exist (static) and are unused. Premiere / FCPXML interchange is later, beside NLE XML, and is not part of the MVP render.

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
