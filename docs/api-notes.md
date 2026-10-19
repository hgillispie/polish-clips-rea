# Descript API notes

Source: `https://staging-docs.descriptapi.com/openapi.yaml`, fetched 2026-10-19. OpenAPI 3.0, `info.version` **1.2**, `info.title` Descript API. Server: `https://descriptapi.com/v1`. Paths below are relative to that server. This file summarizes the operations Polish Clips uses. It is not a dump of the YAML.

Human docs: [https://docs.descriptapi.com/](https://docs.descriptapi.com/). The staging document is the shape authority for this repo when it disagrees with earlier notes.

Tag: OpenAPI shapes in this file are **static** unless a sentence says inferred or unknown. The section **Editor project AI routes** is the web client, build `react19/9a29d61183bce669600a9dd9a1f8588d708becac`. Those claims are **static-bundle** or **decompiled**. That host is `https://api.descript.com`. It is not `https://descriptapi.com`. Chunk 88 contains zero occurrences of `descriptapi.com`.

## Auth, quota, rate limit

- `Authorization: Bearer <token>`. Tokens are created in Descript Settings → API tokens and are scoped to one Drive. The token inherits the user's permissions on that Drive.
- Treat the token like a password. It belongs in an environment variable, never in git.
- **402** `error: payment_required` means quota, not a malformed body.
  - Import: insufficient **media minutes**. Example message: `Insufficient media minutes to start the job (300 minutes required, 50 available)`.
  - Agent: insufficient **AI credits**. Example message: `Insufficient AI credits to start the job (100 credits required, 25 available)`.
- **429** `error: rate_limit_exceeded`. Headers: `Retry-After` (seconds), `X-RateLimit-Remaining`, `X-RateLimit-Consumed`. Wait `Retry-After` before retrying.
- Error JSON for 400, 401, 402, 403, 404, 429 is `{ "error": string, "message": string }`.

There is also a first-party CLI, `@descript/platform-cli` (`descript-api`), which wraps import and agent with its own polling. Polish Clips calls HTTP directly so job handling stays in our code.

## Job states

Shared by import, agent, and publish:

| `job_state` | Meaning |
| --- | --- |
| `queued` | Waiting to start |
| `running` | In progress. Optional `progress.label`, `progress.percent`, `progress.last_update_at` |
| `stopped` | Finished. Read `result.status` |
| `cancelled` | Cancelled |

`result` is present when `job_state` is `stopped`.

| `result.status` | Who | Meaning |
| --- | --- | --- |
| `success` | all | Completed |
| `partial` | import only | Some files imported, some `media_status.*.status = failed` |
| `error` | all | Failed. Read `result.error_message`. Optional `result.error_code` |

A single import file uses `failed`, not `error`. The job uses `error` or `partial`.

`DELETE /jobs/{job_id}` cancels a running job and returns **204**.

`GET /jobs` lists recent jobs (`project_id`, `type`, `cursor`, `limit` 1–100 default 20, `created_after`, `created_before`). Default window is 7 days; max lookback is 30 days. The `type` enum in this snapshot is `import/project_media` and `agent` only. Publish jobs still exist; this list filter does not name them.

`JobStatus` is a discriminator on `job_type` (`import/project_media`, `agent`, `publish`). The mapping also names `export/timeline` → `TimelineExportJobStatus`, and that schema is **absent** from this YAML snapshot. Do not invent timeline-export fields.

## POST /jobs/import/project_media

Creates a project when `project_id` is omitted, imports media, can create compositions, and triggers transcription and background processing. **201** with a job payload. Async.

### Request

| Field | Required | Notes |
| --- | --- | --- |
| `project_id` | no | UUID. Import into this project. Filenames must not collide |
| `project_name` | no | Used when `project_id` is omitted |
| `team_access` | no | `edit` \| `comment` \| `view` \| `none`. Default `none`. New projects only |
| `folder_name` | no | Nested path, `/`-separated. New projects only |
| `workspace_name` | no | Case-insensitive workspace name. `Personal` and `General` are reserved. Unknown name → 404 |
| `add_media` | no | Map of display name → one of the three item shapes below |
| `add_compositions` | no | Each item requires `clips[]` |
| `callback_url` | no | POST the final job status here |

`add_media` item, exactly one shape (`additionalProperties: false` on each):

- **URL.** `{ "url", "language"? }`. URL must be reachable by Descript and must support HTTP Range. Sign for 12–48 hours.
- **Direct upload.** `{ "content_type", "file_size", "language"? }`. `file_size` is bytes.
- **Multitrack.** `{ "tracks": [{ "media", "offset"? }] }`. `offset` is seconds, default 0.

`language` is an ISO 639-1 code. Omitted → auto-detect.

Composition: `{ name?, width? (default 1920), height? (default 1080), fps?, clips: [{ media, mute? }] }`. `fps` is documented as work in progress and **ignored** if sent. `mute: true` on a non-sequence clip mutes the whole script layer.

### 201 response

Required: `job_id`, `drive_id`, `project_id`, `project_url`. Optional: `drive_name`, `upload_urls`.

`upload_urls[displayName]` = `{ upload_url, asset_id, artifact_id }`. `PUT` the raw bytes to `upload_url` with `Content-Type: application/octet-stream`. The URL expires after 3 hours. The job notices the upload and continues. Mix URL items and direct-upload items in one request; `upload_urls` contains only the direct items.

### Stopped result (success or partial)

Required: `status`, `media_status`, `media_seconds_used`. Optional: `created_compositions[]` of `{ id, name }`.

`media_status[displayName]`: `{ status: success\|failed, duration_seconds?, error_message? }`.

### Errors

| HTTP | When |
| --- | --- |
| 400 | Bad body, bad URL, URL not Range-capable, filename collision |
| 401 | Missing or invalid token |
| 402 | Not enough media minutes |
| 403 | No access to the drive or project |
| 404 | Drive or project missing |
| 429 | Rate limit |

Do not edit the project in the Descript UI while the import job is still running. `project_id` returns immediately, before processing finishes (guide text in the spec).

## POST /jobs/agent

Underlord. Natural-language edit. **201**. Async.

Provide **exactly one** of `project_id` (edit) or `project_name` (create). `prompt` is required.

| Field | Required | Notes |
| --- | --- | --- |
| `project_id` | one of | UUID |
| `project_name` | one of | Creates a project |
| `prompt` | yes | Instruction |
| `composition_id` | no | Requires `project_id`. Full UUID, 5-character short id, or a full `https://web.descript.com/{project_id}/{short}` URL |
| `model` | no | Canonical id or alias. Default `auto` |
| `conversation_id` | no | UUID from a previous response. Requires the same `project_id` |
| `team_access` | no | New project only. Same enum as import. Default `none` |
| `callback_url` | no | Same webhook behaviour as import |

### 201 response

Required: `job_id`, `drive_id`, `project_id`, `project_url`, `resolved_model`, `conversation_id`. Optional: `drive_name`.

`conversation_id` is always on this 201. You do not wait for the job to learn it. Pass it back with the same `project_id` to continue the conversation. `resolved_model` is the canonical id, or the string `auto` when the request used `auto`.

### Stopped success result

Required: `status` (`success`), `agent_response` (string), `project_changed` (boolean).

Often present: `media_seconds_used` (integer seconds), `ai_credits_used` (integer), `resolved_model`, `conversation_id`. The schema requires only the first three. Older jobs may omit `resolved_model`. `resolved_model` may be `inherited` when a follow-up keeps the conversation's model.

### Stopped error result

Required: `status` (`error`), `error_message`. Optional: `error_code`, `resolved_model`, `conversation_id`.

A failed agent job still ends at `job_state: stopped`.

### Errors

| HTTP | When |
| --- | --- |
| 400 | Empty prompt, bad id, `conversation_id` belongs to another project |
| 401 | Bad token |
| 402 | Not enough AI credits |
| 403 | Drive admin has disabled agent usage |
| 404 | Project, composition, or conversation not found |
| 429 | Rate limit |

### GET /agent/models

Returns `{ availableModels: [{ id, cost }], aliases: [{ id, resolvesTo, description, cost }] }`. `cost` is `low` \| `medium` \| `high`. The live list is the source of truth; the YAML example is abridged (`auto` / medium, `claude-opus-5.5` / high, `claude-haiku-5.5` / low, alias `claude-opus` → `claude-opus-5.5`). Exact spend is `ai_credits_used` on the job, not the tier.

Official prompt examples in the spec (behavioural targets, not code):

- `remove all filler words`
- `add studio sound to every clip`
- `Add studio sound and captions` (getting-started guide)
- `create a 30-second highlight reel`
- `remove the section from 1:30 to 2:15`
- CLI sample: `Remove filler words and add Studio Sound to all clips`

No schema field on **this** OpenAPI sets filler ignore-versus-delete, caption style, eye contact, a background mask, or lip-sync. Studio Sound intensity is also absent here. The web client is different: see **Editor project AI routes** below. `studioSoundIntensity` exists on the audio ref there, and the speech-enhancement POST sends a model `version`, not a low/medium/high strength.

## POST /export/transcript

Synchronous **200**. Body is the file (`Content-Disposition: attachment`). Header `X-Composition-Id` is the exported composition UUID.

| Field | Required | Notes |
| --- | --- | --- |
| `project_id` | yes | UUID |
| `format` | yes | `txt` \| `markdown` \| `html` \| `rtf` \| `docx` \| `srt` |
| `composition_id` | no | Same three id forms as the agent. Omitted → first composition |
| `include_speaker_labels` | no | `off` \| `changes` (default) \| `every_paragraph` |
| `include_markers` | no | boolean, default false |
| `timecodes` | no | `{ frequency_seconds?, on_paragraphs?, on_speakers?, on_markers?, offset_seconds? }` |

`srt` is a timed SubRip file. `docx` is binary; the others are text. This is **not** a word-level JSON model. Building ignore flags from this export means parsing cues or paragraphs, which are coarser than Whisper words (**inferred** limitation).

Errors: 400, 401, 403, 429. No 402 on this operation in the spec.

## POST /jobs/publish

Secondary for Polish Clips. **201**. Requires `project_id`. Optional: `composition_id` (same id forms; omitted → first composition that has content, skipping an empty placeholder), `media_type` `Video` (default) or `Audio`, `resolution` `480p` \| `720p` \| `1080p` \| `1440p` \| `4K` (video only), `access_level` `public` \| `unlisted` \| `drive` \| `private`, `callback_url`.

Audio-only composition: omitting `media_type` publishes as audio; sending `Video` returns **422** `unprocessable_entity`.

Success result requires `status`, `composition_id`, `share_url`. Also `media_type`, `download_url`, `download_url_expires_at` when signing works. Republish of the same `(project_id, composition_id, media_type)` reuses the share URL.

`GET /projects/{project_id}` returns `media_files` (path → `{ type, duration? }`), `compositions[]` (`id`, `name`, `duration?`, `media_type?`), and `publishes[]` (existing share URLs) without starting a job. Use it to pick `composition_id` after import.

## Other operations (unused by the MVP)

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/projects` | List projects in the token's drive. Filters include `name`, `folder_path`, `created_by=me`, time ranges. Cursor pagination |
| `GET` | `/search` | Drive search across projects, media, transcripts. Up to 100 hits. Visual search is Enterprise-only |
| `GET` | `/status` | Liveness |
| `GET` | `/published_projects/{publishedProjectSlug}` | Public metadata plus a **VTT** `subtitles` string and a time-limited `download_url` |
| `POST` | `/edit_in_descript/schema` | Partner "Edit in Descript" import URL. Access is gated; the spec says to contact Descript. Out of scope |

## Editor project AI routes

Source: chunk `88.fc0ea62a7f115f3adca9.js` of the public web client, sliced 2026-10-19. Not the OpenAPI above. A logged-in editor session calls these. Polish Clips does not ship that session. The shapes are the contract the effect specs follow. An MCP string `https://api.descript.com/v2/mcp` is also present (**static-bundle**). Login-walled responses were not fetched.

Shared helper (**static-bundle**):

- `POST /projects/{projectId}/{endpoint}` with JSON from `payloadJsonFromPayload`.
- `GET /projects/{projectId}/{endpoint}/{taskId}` to poll.
- HTTP 429 is caught and returned as `{id: taskId, state: "hold"}`. That is a wait, not a hard failure.
- If the response has `result`, it is passed through `resultFromResultJson`. Other `state` strings were not named (**unknown**).

| Endpoint | Task name | displayName | artifactType | type | POST body |
| --- | --- | --- | --- | --- | --- |
| `eye_gaze_correction` | `eye_contact` | Eye Contact | `eye_contact` | `artifact` | `{asset_id}` |
| `background_removal` | `background_mask` | background effect (removal or blur) | `background_mask` | `blocking` | `{asset_id}` |
| `face_tracking` | `center_active_speaker` | center active speaker | `face_tracking` | `artifact` | `{asset_id}` |
| `lip_sync` | `imputation_lip_sync` | Video Regenerate | `imputation_lip_sync` | `artifact` | imputation object below |
| `lip_sync` | `translation_lip_sync` | lip-sync | `translation_lip_sync` | `artifact` | translation object below |
| `speech_enhancement` | `studio_sound` | Studio Sound | `speech_enhanced` | `blocking` | `{audio_asset_id, audio_artifact_id, version?}` |

Eye-contact result JSON uses plural `artifact_ids`. Background removal, face tracking, and both lip-sync variants use singular `output_artifact_id`, which the client wraps in a one-element `artifactIds` array. Speech enhancement returns `speech_enhancement_audio_asset_id` and `speech_enhancement_audio_artifact_id`.

`version` on speech enhancement is omitted when `studioSoundModel` is `auto`. Otherwise it is `v1` or `v3_5`. Effect id string `com.descript.studioSound`.

### lip_sync bodies (static-bundle)

Imputation (Video Regenerate). `additionalData` is required or the client throws `"additionalData is required for lip sync"`.

```text
{
  asset_id,
  audio_artifact_id,
  audio_artifact_time_range,    # imputationAudioTimeRange
  prefix_urls,
  suffix_urls,
  to_be_replaced_urls,
  variant: "imputation",
  composition_id
}
```

Translation uses the same path with `variant: "translation"`, `prefix_urls: []`, `suffix_urls: []`, and `audio_artifact_time_range` taken from `dubAudioTimeRange`.

`validTypes` for both lip-sync tasks is `["audio"]` (the driving artifact). `displayInSuperToast` is false. This is not kebab `generate-video`.

### HD effect ids (static-bundle, ~3772069)

`com.descript.backgroundBlur`, `com.descript.backgroundRemoval`, `com.descript.eyeContact`, `com.descript.speakerFocus`, `com.descript.uplighting`, `com.descript.portraitLighting`.

`background_removal.effectTypes` is blur, removal, uplighting, and portrait lighting. One mask artifact serves all four.

### Credits (static-bundle category map)

| Key | Category | Integer recovered |
| --- | --- | --- |
| `eye_contact`, `green_screen`, `background_blur` | `ai_effects` | 10 per use (agent schema) |
| `skin_smoothing` | `ai_effects` | 5 per file, first apply |
| `center_active_speaker` | `ai_effects` | none |
| `studio_sound` | `ai_effects` | none |
| `draft_a_title`, `draft_show_notes`, `draft_youtube_description`, `draft_social_post`, `summarize` | `ai_writing` | none |
| `ai_regenerate_audio` | `ai_speech` | none |
| `lip_sync`, `ai_regenerate_video`, `ai_gen_video` | `ai_media_generation` | none |

Writing actions (`suggest-title`, `youtube-description-v2`, `show-notes-v2`) and the skill `prepare-for-publish` are not these POSTs. They are documented in [pseudocode/youtube-titles-descriptions.md](pseudocode/youtube-titles-descriptions.md).

402 on these project routes was not traced (**unknown**). The OpenAPI 402 rules above stay on `descriptapi.com` only.

## Gaps that change the build

1. No word-level transcript JSON. The open-source stack must produce its own timings (or accept cue-level SRT).
2. No ignore/strikethrough field. Official copy says "remove". Whether Underlord strikes words through or deletes them is **unknown** until a fixture probe compares the exported transcript with the source.
3. The public OpenAPI has no per-feature REST fields for fillers, retakes, Studio Sound, captions, or eye contact. One `/v1/jobs/agent` prompt can ask for several of them; the only structured outcomes on that host are `agent_response`, `project_changed`, and credit counters. The editor client does have project routes for eye gaze, background removal, face tracking, lip sync, and speech enhancement, on `api.descript.com`, documented above. Those are not OpenAPI operations.
4. `fps` on import compositions is ignored.
5. `export/timeline` is named in the job discriminator and undefined in this snapshot.
