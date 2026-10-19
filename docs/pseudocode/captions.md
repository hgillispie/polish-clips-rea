# Captions

Build SRT and VTT cues from **non-ignored** words. Ignored fillers and retakes do not appear in the default caption track. The transcript model is unchanged.

## Input / output

```text
input:
  transcript          Transcript
  options
    max_chars         integer     # default 42
    max_duration      number      # default 6.0 seconds
    max_gap           number      # default 0.6; start a new cue after this silence
    min_duration      number      # default 0.8
output:
  srt                 string
  vtt                 string
  cues                Cue[]

Cue
  index               integer     # 1-based
  start_seconds       number
  end_seconds         number
  text                string
  speaker_id          string | null
  words               CueWord[]   # source words that formed the line; empty for cue alignment

CueWord
  word_id             string
  text                string
  start_seconds       number
  end_seconds         number
```

## Algorithm

```text
function build_captions(transcript, options) -> (srt, vtt, cues):
  words = [w for w in transcript.words if not w.flags.ignored]
  cues = []
  bucket = []

  function flush():
    if bucket is empty:
      return
    text = join_display(bucket)          # single spaces, no leading space
    start = bucket[0].start_seconds
    end = bucket.last.end_seconds
    if end - start < options.min_duration:
      end = start + options.min_duration
    cues.append(Cue(
      index=len(cues)+1, start, end, text,
      speaker_id=bucket[0].speaker_id,
      words=[CueWord(w.id, w.text, w.start_seconds, w.end_seconds) for w in bucket]
    ))
    bucket = []

  for word in words:
    if bucket is empty:
      bucket = [word]
      continue

    gap = word.start_seconds - bucket.last.end_seconds
    speaker_break = word.speaker_id != bucket[0].speaker_id
      and word.speaker_id is not null
      and bucket[0].speaker_id is not null
    projected = join_display(bucket + [word])
    duration = word.end_seconds - bucket[0].start_seconds
    boundary = ends_sentence(bucket.last.text)

    if speaker_break or gap > options.max_gap:
      flush()
      bucket = [word]
    else if len(projected) > options.max_chars or duration > options.max_duration:
      flush()
      bucket = [word]
    else:
      bucket.append(word)
      if boundary and len(join_display(bucket)) >= options.max_chars * 0.6:
        flush()

  flush()
  return format_srt(cues), format_vtt(cues), cues

function ends_sentence(text) -> boolean:
  return text ends with "." or "?" or "!"

function join_display(words) -> string:
  return " ".join(w.text.trim() for w in words if w.text.trim() != "")
```

Cue alignment (`transcript.alignment == "cue"`): each non-ignored "word" is already a line. Emit one cue per line. Do not reflow. Leave `words` empty so karaoke can see that there are no word times.

## SRT and VTT

```text
function format_srt(cues) -> string:
  blocks = []
  for cue in cues:
    blocks.append(
      str(cue.index) + "\n"
      + srt_time(cue.start_seconds) + " --> " + srt_time(cue.end_seconds) + "\n"
      + cue.text + "\n"
    )
  return "\n".join(blocks)

function srt_time(seconds) -> string:
  # 00:00:00,000  (comma before milliseconds)
  clamp seconds at 0
  h, m, s, ms from seconds
  return f"{h:02}:{m:02}:{s:02},{ms:03}"

function format_vtt(cues) -> string:
  body = ["WEBVTT", ""]
  for cue in cues:
    body.append(vtt_time(cue.start_seconds) + " --> " + vtt_time(cue.end_seconds))
    body.append(cue.text)
    body.append("")
  return "\n".join(body)

function vtt_time(seconds) -> string:
  # 00:00:00.000  (dot before milliseconds)
```

UTF-8, no BOM. If `speaker_id` is set and the transcript has more than one speaker, prefix the cue text with the speaker label and a colon (`Speaker 1: ...`). Single-speaker projects omit the prefix.

## Errors

| Case | Behaviour |
| --- | --- |
| No non-ignored words | Return empty SRT (`""`) and a VTT file that is only `WEBVTT\n`. Not a hard failure |
| Word with `end < start` | Reject the transcript; this violates [transcript-model.md](transcript-model.md) |
| Overlapping cues after padding `min_duration` | Pull the previous cue's end back to this cue's start so cues do not overlap |

No 402. This file's required output is the sidecar SRT, the sidecar VTT, and `Cue[]`.

Style (font, color, position, karaoke) is [caption-style.md](caption-style.md). Drawing those cues into frames is [caption-burnin.md](caption-burnin.md), an optional export. Both are local. The OpenAPI has no caption-style schema (static), so Underlord cannot be told a `CaptionStyle`.

## Descript API option

Two different things in the spec (static):

1. Agent prompt `add captions` (or "add classic karaoke-style captions" in the getting-started example). That edits the Descript composition. Style is whatever Underlord does. No caption-style schema.
2. `POST /export/transcript` with `format: "srt"` returns a timed transcript file. That file follows Descript's exporter, which may include words our model would have ignored. Use it as a comparison artifact, not as the editor's caption track, when the open stack is the source of truth.

Combined prompt when the API backend owns the edit:

```text
Add readable captions for the spoken words that remain after filler
and retake cleanup. Break lines at punctuation. Do not caption ignored fillers.
```

402 and polling: [underlord-agent-job.md](underlord-agent-job.md). Export itself has no 402 in the spec; handle 400/401/403/429.

```text
function export_descript_srt(client, project_id, composition_id) -> string:
  response = POST /v1/export/transcript
    { project_id, composition_id, format: "srt", include_speaker_labels: "off" }
  if response.status == 429:
    sleep Retry-After, retry up to 3 times
  if response.status != 200:
    fail response.body.message
  return response.body   # text/plain SubRip
```

## Build options

| Option | Notes |
| --- | --- |
| Local cue builder (this file) | Required. Honors `ignored`. Word spans feed karaoke |
| Local `CaptionStyle` + preview | Required for the editor. [caption-style.md](caption-style.md) |
| Local burn-in | Optional export. [caption-burnin.md](caption-burnin.md) |
| Descript SRT export | Fast check of the server transcript. Cue-level, may still contain fillers |
| Underlord "add captions" | In-project captions, credit-metered, style uncontrolled |
