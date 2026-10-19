# Clip cut

Cut a clip from a transcript selection. The clip contains the **kept** ranges inside that selection (ignored fillers and retakes are skipped). The source file and the full transcript stay intact. The clip is a new media file plus a new transcript whose clocks are shifted to start at zero.

## Input / output

```text
input:
  transcript       Transcript
  media            MediaAsset          # original, or enhanced audio muxed with video
  selection        Selection           # two word ids, see transcript-model.md
  options
    skip_ignored   boolean             # default true
    video          boolean             # default media.has_video
output:
  clip_media       MediaAsset
  clip_transcript  Transcript          # alignment preserved; times rebased
  report
    source_ranges  KeptRange[]
    duration_seconds number
```

## Resolve the selection

```text
function selection_bounds(transcript, selection) -> (start_word, end_word):
  a = index_of(selection.anchor_word_id)
  b = index_of(selection.focus_word_id)
  if a is missing or b is missing:
    fail "selection word is not in this transcript"
  lo, hi = min(a, b), max(a, b)
  return transcript.words[lo], transcript.words[hi]
```

The inclusive word span is `[start_word, end_word]` in time order.

## Algorithm

```text
function cut_clip(transcript, media, selection, options) -> output:
  first, last = selection_bounds(transcript, selection)
  span_words = words from first through last inclusive

  if options.skip_ignored:
    kept = [w for w in span_words if not w.flags.ignored]
  else:
    kept = span_words

  if kept is empty:
    fail "selection has no words to play"

  ranges = kept_ranges_of(kept)       # same merge rules as transcript-model, PAD_SECONDS 0.02
  clip_path = ffmpeg_concat(media, ranges, want_video=options.video)

  # Rebase words onto the concatenated clock.
  clip_words = []
  cursor = 0
  for range in ranges:
    span = range.end_seconds - range.start_seconds
    for word in words_in(range):
      clip_words.append(copy(word,
        start_seconds = word.start_seconds - range.start_seconds + cursor,
        end_seconds   = word.end_seconds   - range.start_seconds + cursor
      ))
    cursor += span

  clip_transcript = Transcript(
    id=new_id(),
    media_id=new_id(),
    words=clip_words,
    alignment=transcript.alignment,
    language=transcript.language,
    duration_seconds=cursor,
    speakers=transcript.speakers,
    asr_model=transcript.asr_model
  )
  return clip_media(path=clip_path, duration_seconds=cursor), clip_transcript,
         report(source_ranges=ranges, duration_seconds=cursor)
```

`ffmpeg_concat` trims each source range and concatenates. Prefer stream copy when every boundary is on a keyframe; otherwise re-encode video (`libx264`) and audio (`aac`). Audio-only input writes m4a or wav and ignores `options.video`.

If an enhanced audio asset is active, map the enhanced wav as the audio input and the original video as the video input, using the same source-clock ranges. If the enhanced asset was discarded for a duration mismatch, cut the original audio.

## Errors

| Case | Behaviour |
| --- | --- |
| Unknown word id | Fail before ffmpeg runs |
| All words ignored | Fail with "selection has no words to play". Offer `skip_ignored=false` |
| ffmpeg non-zero exit | Fail with stderr tail. Leave no partial file |
| Zero duration after trim | Fail. Do not upload an empty clip |

No 402 on the local path.

## Descript API option

No clip-cut schema (static). The spec's examples are coarse prompts, for example `create a 30-second highlight reel` and `remove the section from 1:30 to 2:15`. A selection-shaped prompt:

```text
Create a new composition that keeps only the speech from {start} to {end}.
Skip filler words and earlier retakes. Name the composition "Polish clip".
```

`start` and `end` are source-clock timestamps (`m:ss.s`) of `first.start_seconds` and `last.end_seconds`. This prompt cannot carry word ids. After the job, read `GET /projects/{project_id}` and take the new composition id (the one that was not in the pre-job list). If `project_changed` is false, do not invent a composition.

Use this only in the `descript_api` backend. The local editor's clip is the one that honors `ignored`.

## Build options

| Option | Notes |
| --- | --- |
| ffmpeg trim + concat (this file) | Default. Word-accurate given the transcript clock |
| Underlord highlight prompt | Useful when the user asked for "a short clip" with no selection. Not a substitute for a word selection |
| NLE XML export | Out of scope for the MVP. rescript publishes this idea; we do not copy that code ([../reuse-rescript.md](../reuse-rescript.md)) |
