# Feature inventory

Scope lock for Polish Clips. Each row is a behaviour we intend to build, mapped to the Descript API where the OpenAPI (version 1.2, 2026-10-19) has an operation. "Observed cost" stays empty until a test-Drive token probe.

Evidence: API column is **static**. Product behaviour that the spec does not name (ignore versus hard delete, Studio Sound intensity, eye contact) is **inferred** from Descript's product language and is unverified against a live account.

## Pipeline

| Feature | MVP | Input | Output | Where it runs | API | Open stack | Observed cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Import + transcribe | yes | Local file or URL, language hint | Project or local media id; word timings | Server via API, or on-device ASR | `POST /jobs/import/project_media` then poll. Transcription is part of import (static). No word-JSON endpoint | ffmpeg decode + Whisper-class ASR with word timestamps | |
| Filler removal | yes | Transcript words | Same words with `ignored=true` on fillers | Local model. API path is a prompt | `POST /jobs/agent` prompt. Official example text is "remove all filler words" (static). Ignore/strikethrough is not a field | Lexicon + context filter; set ignore, do not delete the word | |
| Retake removal | yes | Transcript utterances | Earlier takes marked ignored | Local model, or one agent prompt | Prompt only. No retake schema | Near-duplicate utterance match; keep the last take | |
| Studio Sound–class enhance | yes | Speech audio | Enhanced audio, original kept | Local denoiser, or agent prompt | Prompt "add studio sound". No intensity parameter (static) | RNNoise-class or DeepFilterNet-class; ffmpeg `afftdn` as a weak baseline | |
| Captions | yes | Non-ignored words | SRT and VTT cues | Local grouper. API can also add captions inside a project | Agent prompt "add captions". `POST /export/transcript` `format: srt` returns a timed transcript file (static) | Cue builder in [pseudocode/captions.md](pseudocode/captions.md) | |
| Clip cut | yes | Word or time selection | New clip of kept ranges inside the selection | Local ffmpeg trim/concat, or a coarse agent prompt | Prompt only ("create a 30-second highlight reel" is the spec example) | Selection → kept ranges → encode | |
| Publish / export | secondary | Composition or local master | File, or share URL + download URL | API publish job, or local encode | `POST /jobs/publish`; `GET /projects/{id}` lists existing `publishes` | ffmpeg encode; no share page | |

## Research note (non-blocking)

| Feature | MVP | What we know | What we will not do yet |
| --- | --- | --- | --- |
| Eye contact | no | Descript markets an eye-contact correction. The OpenAPI has no operation, schema field, or example prompt for it (static). It might be prompt-only or UI-only (**inferred**, unknown) | Do not add a pipeline stage. A later token probe can try one explicit prompt and record `project_changed` plus `agent_response`. Failure or a vague reply leaves the feature unknown |

## Explicitly out of scope

Translate / dub, green screen, Overdub and other voice clones, screen recording, Rooms, comments, Drive collaboration, Premiere/FCPXML interchange, Brand Studio, layout packs. `GET /search` and `POST /edit_in_descript/schema` exist (static) and are unused by this pipeline.

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
