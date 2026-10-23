# Underlord agent job

Two surfaces. They are not interchangeable.

1. **Public API.** `POST /v1/jobs/agent` on `https://descriptapi.com/v1`. Shapes match the staging OpenAPI 1.2 snapshot (2026-10-19), summarized in [../api-notes.md](../api-notes.md). This is the client below.
2. **Web client (the in-editor agent).** A different runtime: an agent loop in the browser (or Descript's cloud agent) calling `POST /agent/completions` and running about 86 tools over the project document. It is fully documented in [../descript-analysis/underlord/](../descript-analysis/underlord/), and our own pseudocode for it is in [underlord/](underlord/). `descriptapi.com` does not appear in the web chunks (**static-bundle**). This file covers only the public API client.

## Input / output

```text
input:
  token              string          # Bearer; from the environment, never logged
  request
    project_id       string | null   # exactly one of project_id, project_name
    project_name     string | null
    prompt           string
    composition_id   string | null
    conversation_id  string | null
    model            string | null   # default server-side "auto"
    callback_url     string | null
  poll
    timeout_seconds  number          # default 900
    initial_delay    number          # default 2
    max_delay        number          # default 15
output:
  submission         # 201 body
  job                # final GET body
  credits
    ai_credits_used      integer | null
    media_seconds_used   integer | null
```

## Submit

```text
function submit_agent(token, request) -> submission:
  if (request.project_id is null) == (request.project_name is null):
    fail "send exactly one of project_id or project_name"
  if request.prompt.trim() == "":
    fail "prompt is empty"
  if request.composition_id and request.project_id is null:
    fail "composition_id requires project_id"
  if request.conversation_id and request.project_id is null:
    fail "conversation_id requires project_id"

  body = { prompt: request.prompt }
  copy over whichever of project_id or project_name is set
  copy composition_id, conversation_id, model, callback_url when set

  response = POST /v1/jobs/agent
    headers: Authorization: Bearer token, Content-Type: application/json
    body: body

  if response.status == 429:
    sleep Retry-After (or 2s if the header is missing)
    retry this POST up to 3 times, then fail "rate limited"
  if response.status == 402:
    fail QuotaError(kind="ai_credits", message=response.body.message)
  if response.status == 403:
    fail "agent disabled or forbidden: " + response.body.message
  if response.status == 400 or 404 or 401:
    fail response.body.error + ": " + response.body.message
  if response.status != 201:
    fail "unexpected " + response.status

  submission = response.body
  # required: job_id, drive_id, project_id, project_url, resolved_model, conversation_id
  return submission
```

Store `submission.conversation_id` immediately. A follow-up edit sends it back with the same `project_id`.

## Poll

```text
function poll_job(token, job_id, poll) -> job:
  delay = poll.initial_delay
  deadline = now + poll.timeout_seconds

  while now < deadline:
    response = GET /v1/jobs/{job_id}
      headers: Authorization: Bearer token

    if response.status == 429:
      sleep Retry-After
      continue
    if response.status == 404:
      fail "job not found"
    if response.status == 401 or 403:
      fail response.body.message
    if response.status != 200:
      fail "unexpected " + response.status

    job = response.body
    if job.job_state == "queued" or job.job_state == "running":
      emit progress(job.progress.label, job.progress.percent)   # label may be absent
      sleep delay
      delay = min(poll.max_delay, delay * 1.5)
      continue
    if job.job_state == "cancelled":
      fail "job cancelled"
    if job.job_state == "stopped":
      return job
    fail "unknown job_state " + job.job_state

  # Timed out locally. The server job may still be running.
  DELETE /v1/jobs/{job_id}     # best-effort cancel; ignore 404
  fail "timed out after " + poll.timeout_seconds + "s"
```

```text
function finish(job) -> output:
  if job.result is null:
    fail "stopped job without result"
  if job.result.status == "error":
    fail job.result.error_message
  if job.result.status != "success":
    fail "unexpected result.status " + job.result.status

  return {
    job: job,
    agent_response: job.result.agent_response,
    project_changed: job.result.project_changed,
    credits: {
      ai_credits_used: job.result.ai_credits_used,        # may be absent
      media_seconds_used: job.result.media_seconds_used
    },
    conversation_id: job.result.conversation_id or job.conversation_id
  }
```

`callback_url` does not replace a final GET. When a callback arrives, still GET the job once and trust the GET body. Verify the callback came from your own receiver; the spec does not document a signature (unknown). If you cannot verify, ignore the push and rely on polling.

## 402 handling

```text
on QuotaError(kind="ai_credits"):
  do not retry
  do not fall through to publish
  show response.message to the operator
  leave the Descript project as it was
  the open-stack pipeline may continue without this backend
```

Import jobs use the same poll function and a different 402 kind (`media_minutes`). See [polish-pipeline.md](polish-pipeline.md).

## Example prompts

One job can ask for the whole polish. Official examples are shorter; this combined prompt is ours and is **unverified** against a live token:

```text
Do these three edits and nothing else:
1. Strike through filler words (um, uh, and similar) so they do not play,
   and keep them in the transcript so they can be restored.
2. Add Studio Sound at a medium intensity if intensity is available.
3. Add captions for the words that still play.
Do not translate, dub, or change eye contact.
```

Separate prompts, if you want one credit line per effect. Each is a new POST. Pass `conversation_id` from the previous 201 so Underlord sees the earlier turn:

```text
Strike through filler words such as "um" and "uh" so they do not play.
Keep the words in the transcript so they can be restored.
```

```text
Add Studio Sound to the speech. Medium intensity if you can set one.
Do not change which words play.
```

```text
Add captions for the words that still play. Break lines at punctuation.
```

Spec examples you can use as a control, when you want to see default Underlord behaviour rather than ignore semantics:

```text
remove all filler words
add studio sound to every clip
Add studio sound and captions
```

## Read-back

The 201 and the stopped job do not include the transcript. To see what changed:

```text
GET /v1/projects/{project_id}          # compositions, durations
POST /v1/export/transcript
  { project_id, composition_id, format: "txt", include_speaker_labels: "off" }
POST /v1/export/transcript
  { project_id, composition_id, format: "srt", include_speaker_labels: "off" }
```

Compare `txt` to the pre-job transcript. Missing fillers mean a hard delete. Present fillers mean they survived (possibly struck through, which plain text may not show). That ambiguity is why the open stack owns ignore flags.

## Errors (summary)

| HTTP or state | Action |
| --- | --- |
| 400 | Fix the body. Do not retry blindly |
| 401 | Token missing or revoked |
| 402 | Stop. AI credits on this endpoint |
| 403 | Agent disabled by a drive admin, or no access |
| 404 | Project, composition, or conversation id is wrong |
| 429 | Sleep `Retry-After`, max 3 retries on submit; on poll, wait and continue until timeout |
| `result.status == error` | Fail with `error_message` |
| `project_changed == false` | Job succeeded and edited nothing. Report `agent_response` |
| Local timeout | Best-effort `DELETE`, then fail |

## In-app action ids (static-bundle)

Kebab enum in chunk 88 near offset ~1995267. The recovered slice starts at `RemoveRetakes`; earlier members are from the same enum via the symbol index. These are action names, not OpenAPI fields.

| Enum | Wire id | Where it is specified |
| --- | --- | --- |
| `SuggestTitle` | `suggest-title` | [youtube-titles-descriptions.md](youtube-titles-descriptions.md) |
| `ShowNotes` | `show-notes-v2` | same |
| `YouTubeDescription` | `youtube-description-v2` | same |
| `YouTubeThumbnail` | `youtube-thumbnail` | skill may offer it; not implemented |
| `SocialPosts` | `social-posts` | same publish spec |
| `Summarize` | `summarize-v2` | credit `summarize` → `ai_writing` |
| `WriteScript` | `write-script` | credit `write_script` → `ai_writing` |
| `Translate` | `translate` | out of the default build |
| `GenerateImage` | `generate-image` | generative set |
| `GenerateVideo` | `generate-video` | generative set. Not Video Regenerate |
| `GenerateMusic` | `generate-music` | generative set |
| `GenerateSfx` | `generate-sfx` | generative set |
| `CenterActiveSpeaker` | `center-active-speaker` | [center-active-speaker.md](center-active-speaker.md) |
| `CenterActiveSpeakerV2` | `center-active-speaker-v2` | same effect, v2 delta unknown |
| `SmoothJumpCuts` | `smooth-jump-cuts` | credit `smooth_jump_cuts` → `ai_editing`. Not `lip_sync` |
| `RemoveRetakes` | `remove-retakes-v2` | local retake ignore still owns the flag |
| `EditImageInCanvas` | `edit-image-in-canvas` | not this pipeline |
| `SmartZooms` | `smart-zooms` | credit `smart_zooms` → `ai_effects` |
| `WindowDressing` | `window-dressing` | not specified |
| `SegmentWithText` | `segment-with-text` | not specified |
| `AnimateText` | `animate-text` | not specified |

Also on the action inventory (**static-bundle**): `generate-eye-contact`, `generate-studio-sound`, `remove-filler-words`, `add-chapters`.

`generate-video` is grouped with `generate-image`, `generate-music`, `generate-sfx`, and `youtube-thumbnail`. Video Regenerate is `lip_sync` variant `imputation` ([video-regenerate.md](video-regenerate.md)). Do not map one onto the other.

Credit categories for the polish set:

| Key | Category |
| --- | --- |
| `remove_filler_words` | `script_editing` |
| `remove_retakes`, `smooth_jump_cuts`, `add_chapters` | `ai_editing` |
| `studio_sound`, `eye_contact`, `green_screen`, `background_blur`, `skin_smoothing`, `center_active_speaker` | `ai_effects` |
| `draft_a_title`, `draft_show_notes`, `draft_youtube_description`, `draft_social_post`, `summarize` | `ai_writing` |
| `ai_regenerate_audio` | `ai_speech` |
| `lip_sync`, `ai_regenerate_video`, `ai_gen_video` | `ai_media_generation` |

A public agent prompt that says "do not change eye contact" is still the right instruction for `/v1/jobs/agent`, because that route has no eye-contact field and a prose request might otherwise hit the in-app action.

## Skill `prepare-for-publish` (static-bundle)

```text
id:            prepare-for-publish
name:          Prepare for publish
isInvokable:   true
isViewable:    true
gate:          feature flag agent-first-party-macro-skills is true
```

The description says the result is titles, a YouTube description with chapters, platform social posts, and a thumbnail, and that this is text and images only. Steps the skill string requires, in our words:

1. Ask platform and audience, then optionally tone. One question at a time.
2. Draft several titles (`suggest-title`).
3. Draft a YouTube description with chapters (`youtube-description-v2`). Over 10 minutes, the skill asks for spaced teaser timestamps and SEO hashtags.
4. Draft social posts (`social-posts`).
5. Offer a YouTube thumbnail (`youtube-thumbnail`) when YouTube is a destination.
6. Offer to iterate. Do not export, render, publish, or change the edit unless the user explicitly asks.

Implementation of 1–4 and the timestamp rule: [youtube-titles-descriptions.md](youtube-titles-descriptions.md). The skill body is not copied into source.

Other skills refer to this id when they want a publish package with show notes.

## Build options

| Option | Notes |
| --- | --- |
| This client inside the `descript_api` backend | One combined prompt per fixture, or three follow-ups sharing `conversation_id` |
| `GET /agent/models` before submit | Optional. Pass `model` from `availableModels[].id` or an alias. Omit `model` to use `auto` |
| Skip Underlord | Open stack performs filler, retake, enhance, captions, and cut with no token |
| Kebab actions and `prepare-for-publish` | In-app ids. Not fields on `POST /v1/jobs/agent` |
| Project AI routes on `api.descript.com` | Eye contact, mask, face tracking, lip sync, speech enhancement. See [../api-notes.md](../api-notes.md) |
