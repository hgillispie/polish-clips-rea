# Polish pipeline

End-to-end orchestration for one clip. Stages call the specs next to this file. This file is the order, the shared context, and the backend switch. No stage pastes Descript source.

## Input / output

```text
input:
  source
    path             string          # local media you own
    language         string | null   # BCP-47; null = auto
  backend            "open" | "hybrid" | "descript_api"
  descript                             # required for "hybrid" and "descript_api"
    token            string          # env var, never stored in the project JSON
    project_name     string
  selection          Selection | null   # null = the whole transcript is the clip
  options
    enhance_backend  "deepfilter" | "rnnoise" | "ffmpeg_afftdn" | "descript_prompt"
    enhance_strength "low" | "medium" | "high"
    skip_ignored     boolean         # default true
    publish          boolean         # default false; descript_api backend only
output:
  transcript         Transcript      # with filler and retake flags
  enhanced           MediaAsset | null
  captions_srt       string
  captions_vtt       string
  clip               MediaAsset
  report             PipelineReport

PipelineReport
  backend            string
  stages             { name, ok, detail }[]
  descript
    project_id       string | null
    project_url      string | null
    composition_id   string | null
    conversation_id  string | null
    ai_credits_used  integer | null
    media_seconds_used integer | null
    agent_response   string | null
```

Eye contact is not a stage. If a caller passes an eye-contact flag, record `stages += { name: "eye_contact", ok: false, detail: "research only" }` and continue.

## Shared order

```text
function polish(input) -> output:
  report = empty PipelineReport(backend=input.backend)
  asset = ingest_local(input.source.path)

  if input.backend == "descript_api":
    return polish_black_box(input, asset, report)                  # below

  transcript = transcribe(asset, input.source.language)            # word alignment
  report.stage("transcribe", ok=true, detail="word")

  if input.backend == "hybrid":
    # Side job. Local words stay the editor copy.
    report.descript = try_descript_side_job(input, asset, transcript)

  transcript, filler_report = remove_fillers(transcript, default_options)
  report.stage("fillers", ok=filler_report.skipped_reason is null,
               detail=filler_report)

  transcript, retake_report = remove_retakes(transcript, default_options)
  report.stage("retakes", ok=true, detail=count(retake_report.groups))

  if input.options.enhance_backend == "descript_prompt":
    enhanced, enh_report = enhance_via_agent(input, report)        # may 402
  else:
    enhanced, enh_report = enhance(asset, local_options(input))    # studio-sound.md
  report.stage("enhance", ok=enhanced is not null, detail=enh_report.backend)

  playback_media = asset
  if enhanced is not null and enh_report.backend != "descript_prompt":
    playback_media = mux_video_with(asset, enhanced)               # video clock unchanged

  srt, vtt, cues = build_captions(transcript, default_caption_options)
  report.stage("captions", ok=true, detail=len(cues))

  selection = input.selection or whole_transcript_selection(transcript)
  clip, clip_transcript, cut_report = cut_clip(
    transcript, playback_media, selection, { skip_ignored: input.options.skip_ignored }
  )
  report.stage("clip", ok=true, detail=cut_report.duration_seconds)

  write_sidecars(clip, srt, vtt, transcript_json=transcript)
  return { transcript, enhanced, captions_srt: srt, captions_vtt: vtt, clip, report }
```

`whole_transcript_selection` uses the first and last word ids. `write_sidecars` places the SRT, VTT, and `polish.transcript.v1` JSON next to the clip file, outside git if that directory is a capture folder.

Default `backend` for a later implementation is `open`. Choose `hybrid` when a test-Drive token exists and you want a diff against Underlord. Choose `descript_api` only when the Descript project, not the local ignore flags, is the deliverable.

## Open backend

```text
function ingest_local(path) -> MediaAsset:
  probe = ffprobe(path)                 # duration, video stream present, sample rate
  if probe.duration_seconds <= 0:
    fail "media has no duration"
  return MediaAsset(...)
```

`transcribe` is the local ASR path in [transcript-model.md](transcript-model.md). Suggested default model class: a Whisper checkpoint that returns word timestamps. Speaker diarization is optional; retake removal still runs without it.

This backend never calls Descript, so it cannot return 402.

## Descript API backend

Use a test Drive. The token stays in the environment.

```text
function ingest_descript(input) -> (asset, transcript, ids):
  size = file_size(input.source.path)
  mime = sniff_mime(input.source.path)          # video/mp4, audio/wav, ...
  name = basename(input.source.path)

  created = POST /v1/jobs/import/project_media
    {
      project_name: input.descript.project_name,
      add_media: {
        name: { content_type: mime, file_size: size, language?: input.source.language }
      },
      add_compositions: [
        { name: "Polish", clips: [ { media: name } ] }
      ]
    }
  if created.status == 402:
    fail QuotaError(kind="media_minutes", message=created.body.message)
  if created.status == 429:
    honor Retry-After, retry submit up to 3 times
  if created.status != 201:
    fail created.body.message

  upload = created.body.upload_urls[name]
  PUT upload.upload_url
    headers: Content-Type: application/octet-stream
    body: file bytes
  if PUT status is not 2xx:
    fail "direct upload failed"

  job = poll_job(input.descript.token, created.body.job_id, timeout_seconds=1800)
  if job.result.status == "error":
    fail job.result.error_message
  if job.result.status == "partial":
    entry = job.result.media_status[name]
    if entry.status == "failed":
      fail entry.error_message
  if job.result.media_status[name].status != "success":
    fail "import did not succeed"

  composition_id = job.result.created_compositions[0].id
    or GET /v1/projects/{project_id} and take compositions[0].id

  srt = POST /v1/export/transcript
    { project_id, composition_id, format: "srt", include_speaker_labels: "off" }

  asset = ingest_local(input.source.path)         # local file remains the media clock
  transcript = transcript_from_srt(srt, asset)    # alignment "cue"
  return asset, transcript, {
    project_id, project_url: created.body.project_url,
    composition_id,
    media_seconds_used: job.result.media_seconds_used
  }
```

`ingest_descript` returns cue alignment. The black-box path below is the only caller that treats that SRT as the transcript. `open` and `hybrid` keep the local word transcript.

### Hybrid side job

```text
function try_descript_side_job(input, asset, local_transcript) -> descript report | null:
  try:
    _, cue_transcript, ids = ingest_descript(input)
    agent = underlord_polish(ids, input.descript.token)     # 402 raises QuotaError
    server_srt = POST /v1/export/transcript { format: "srt", ... }
    ids.agent_response = agent.agent_response
    ids.ai_credits_used = agent.credits.ai_credits_used
    ids.server_srt = server_srt          # diff against local captions; do not replace local words
    ids.cue_preview = cue_transcript
    return ids
  catch QuotaError:
    return { error: "402", message }     # caller continues with local stages
  catch error:
    return { error: error.message }
```

A 402 or an agent `error` does not fail `polish`. The report records it. Local filler, retake, enhance, captions, and cut still run.

### Black-box path

`polish_black_box` is for `backend == "descript_api"`. The operator accepts that ignore-versus-delete is unverified and that captions may be cue-level.

```text
function underlord_polish(ids, token) -> agent_result:
  prompt = """
    Do these edits and nothing else:
    1. Strike through filler words (um, uh, and similar) so they do not play,
       and keep them in the transcript so they can be restored.
    2. Remove retakes, keeping the last complete take.
    3. Add Studio Sound at a medium intensity if you can set one.
    4. Add captions for the words that still play.
    Do not translate, dub, or change eye contact.
  """
  submission = submit_agent(token, {
    project_id: ids.project_id,
    composition_id: ids.composition_id,
    prompt: prompt
  })
  job = poll_job(token, submission.job_id, timeout_seconds=900)
  return finish(job)                    # raises when result.status == "error"
```

`submit_agent` turns HTTP 402 into `QuotaError(kind="ai_credits")` and does not retry. `try_descript_side_job` catches that and returns it in the report. `polish_black_box` does not catch it.

```text
function polish_black_box(input, asset, report) -> output:
  _, transcript, ids = ingest_descript(input)
  report.descript = ids
  agent = underlord_polish(ids, input.descript.token)
  report.descript.agent_response = agent.agent_response
  report.descript.ai_credits_used = agent.credits.ai_credits_used
  report.descript.conversation_id = agent.conversation_id
  srt = POST /v1/export/transcript
    { project_id: ids.project_id, composition_id: ids.composition_id,
      format: "srt", include_speaker_labels: "off" }
  vtt = srt_to_vtt(srt)                  # punctuation swap only; cues stay as exported
  if input.options.publish == true:
    report.descript.publish = publish_composition(ids)    # 422 → retry Audio once
  report.stage("underlord", ok=agent.project_changed, detail=agent.agent_response)
  return { transcript, enhanced: null, captions_srt: srt, captions_vtt: vtt,
           clip: asset, report }
```

Publish stays off unless `options.publish` is true. `publish_composition` posts `POST /v1/jobs/publish` with `media_type: "Video"` and `resolution: "1080p"`, then polls. HTTP 422 means the composition has no video; retry once with `media_type: "Audio"`.

On `QuotaError` from `underlord_polish`, `polish_black_box` fails the run. Unlike `hybrid`, there is no local word model to fall back to unless the caller re-runs with `backend: "open"`.

## Stage failure policy

| Stage | Failure | Continue? |
| --- | --- | --- |
| Ingest / probe | Bad file | No |
| Import 402 | No media minutes | `hybrid` records the error and continues locally. `descript_api` stops |
| Import `partial` / file `failed` | Required file missing | `hybrid` records it and continues locally. `descript_api` stops |
| ASR | Worker error | No word pipeline. API-only black box may still run Underlord |
| Fillers skipped | Cue alignment | Yes, reported |
| Enhance | Model or 402 | Yes, on the original audio |
| Captions | Empty word list | Yes, empty sidecar |
| Clip | Empty selection | No |
| Agent 402 / error | Credits or `error_message` | `hybrid`: yes, local stages still run. `descript_api`: no |

## Build options

| Backend | When to choose it |
| --- | --- |
| `open` | Default MVP. Ignore semantics, no token, no credits. Editor behaviour from these specs, informed by rescript's public feature list and not by its code ([../reuse-rescript.md](../reuse-rescript.md)) |
| `descript_api` | You want Underlord's Studio Sound or a publish URL, and you accept that ignore-versus-delete is unverified |
| Hybrid (local transcript + optional agent) | Best reading of the current evidence. The editor owns words. The API is a job you can diff. Described above; turn it on by running `transcribe` even when an import exists |

Hypothesis, not a result: this hybrid beats cloning `web.descript.com` for the Polish Clips MVP. Phase 6 of [../../DESCRIPT_RE_PLAN.md](../../DESCRIPT_RE_PLAN.md) is the check, using the three fixtures in [../feature-inventory.md](../feature-inventory.md).
