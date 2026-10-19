# Underlord agent job

Client for `POST /v1/jobs/agent` and the poll that follows. Shapes match the staging OpenAPI 1.2 snapshot (2026-10-19), summarized in [../api-notes.md](../api-notes.md). Base URL: `https://descriptapi.com/v1`.

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

## Build options

| Option | Notes |
| --- | --- |
| This client inside the `descript_api` backend | One combined prompt per fixture, or three follow-ups sharing `conversation_id` |
| `GET /agent/models` before submit | Optional. Pass `model` from `availableModels[].id` or an alias. Omit `model` to use `auto` |
| Skip Underlord | Open stack performs filler, retake, enhance, captions, and cut with no token |
