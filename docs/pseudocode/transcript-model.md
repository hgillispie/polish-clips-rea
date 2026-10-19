# Transcript model

The editor's source of truth. Later stages (filler, retake, captions, clip cut) read and write this structure. They do not keep a second copy of the words.

Build this in the open-source stack. The Descript API does not return it (static: `POST /export/transcript` is a file, not word JSON). See [../api-notes.md](../api-notes.md).

## Types

```text
MediaAsset
  id                 string
  filename           string
  duration_seconds   number
  sample_rate        integer          # after decode; 16000 for ASR input
  channels           integer
  has_video          boolean
  path               string           # local path; never a bearer token

Speaker
  id                 string
  label              string           # "Speaker 1" until a human renames it

Word
  id                 string           # stable for the life of the transcript
  text               string           # display text, original casing
  start_seconds      number           # inclusive, on the source media clock
  end_seconds        number           # exclusive
  speaker_id         string | null
  confidence         number | null    # 0..1 when the ASR provides it
  flags
    filler           boolean          # detector's opinion
    retake           boolean
    retake_group_id  string | null    # words in one abandoned take share this
    ignored          boolean          # playback and default export skip this word
  source             "asr" | "imported_cue" | "manual"

Transcript
  id                 string
  media_id           string
  language           string           # BCP-47, e.g. "en"
  duration_seconds   number
  words              Word[]           # time order, ids unique
  speakers           Speaker[]
  alignment          "word" | "cue"   # cue = SRT/VTT line, not a real word
  asr_model          string | null

KeptRange
  start_seconds      number
  end_seconds        number
  word_ids           string[]         # non-ignored words that formed the range

Selection
  anchor_word_id     string
  focus_word_id      string           # inclusive word span, either direction
```

Times are seconds as floats on the **source** media clock. Ignoring a word does not shift later words' timestamps. That keeps restore cheap and keeps captions aligned to the original recording.

## Ignore versus delete

`ignored` is the edit. The word stays in `words` so the UI can draw a strikethrough and the operator can turn the flag off.

```text
function set_ignored(transcript, word_ids, ignored):
  for id in word_ids:
    word = transcript.words.by_id(id)
    word.flags.ignored = ignored
  return transcript
```

Hard delete (removing the `Word` and splicing the file) is not the filler operation. Export may omit ignored audio; the model still has the word.

`alignment: "cue"` means each `Word.text` is a whole caption line. Filler and retake detectors must refuse cue alignment or must first split lines into tokens and mark those tokens `confidence: null` with approximate times (spread evenly across the cue). Approximate times are **inferred** and must be labeled in the UI.

## Playback ranges

```text
PAD_SECONDS = 0.02          # tunable; avoids clipping the next phoneme

function kept_ranges(transcript) -> KeptRange[]:
  ranges = []
  current = null
  for word in transcript.words:
    if word.flags.ignored:
      if current is not null:
        ranges.append(current)
        current = null
      continue
    if current is null:
      current = KeptRange(word.start_seconds, word.end_seconds, [word.id])
    else if word.start_seconds - current.end_seconds <= PAD_SECONDS:
      current.end_seconds = word.end_seconds
      current.word_ids.append(word.id)
    else:
      ranges.append(current)
      current = KeptRange(word.start_seconds, word.end_seconds, [word.id])
  if current is not null:
    ranges.append(current)
  return ranges
```

Playback seeks through `kept_ranges` in order. A gap between ranges is a cut. Silence inside a non-ignored word is kept.

## Serialization

JSON document, UTF-8, schema name `polish.transcript.v1`:

```text
{
  "schema": "polish.transcript.v1",
  "transcript": { ...Transcript },
  "media": { ...MediaAsset }
}
```

Round-trip must preserve word ids and flags. Unknown flags are kept, not dropped, so a newer detector can stash extra keys later.

## Building a transcript

### From a local ASR (open stack, default)

```text
function transcribe(asset, language | null) -> Transcript:
  pcm = ffmpeg_decode(asset.path, sample_rate=16000, channels=1)
  raw = whisper_word_timestamps(pcm, language)   # list of {text, start, end, confidence?}
  speakers = diarize(pcm)                         # optional; null speaker_id if skipped
  words = []
  for token in raw:
    words.append(Word(
      id=new_id(),
      text=token.text,
      start_seconds=token.start,
      end_seconds=token.end,
      speaker_id=speaker_at(speakers, token.start),
      confidence=token.confidence,
      flags={filler:false, retake:false, retake_group_id:null, ignored:false},
      source="asr"
    ))
  return Transcript(..., alignment="word", words=words)
```

Run ASR in a worker. The UI stays responsive. If the worker fails, surface the ASR error and leave the asset imported with an empty transcript. Do not invent words.

### From Descript SRT (API backend, coarse)

```text
function transcript_from_srt(srt_text, media) -> Transcript:
  cues = parse_srt(srt_text)          # {index, start, end, text}
  words = []
  for cue in cues:
    words.append(Word(
      id=new_id(),
      text=cue.text,
      start_seconds=cue.start,
      end_seconds=cue.end,
      speaker_id=null,
      confidence=null,
      flags=all false,
      source="imported_cue"
    ))
  return Transcript(..., alignment="cue", words=words)
```

Use this only as a preview of what Underlord left behind. Prefer a local word-level ASR pass on the same file when ignore semantics matter.

## Invariants

- `words` sorted by `start_seconds`, then `end_seconds`.
- `start_seconds < end_seconds` for every word. Drop or repair zero-length ASR tokens before insert.
- Word intervals may touch; they must not be inverted. Small overlaps (ASR jitter under 30 ms) are clamped so `start = max(start, previous.end)`.
- `ignored` does not imply `filler` or `retake`. A manual strike sets only `ignored`.
- Restoring a word clears `ignored` and leaves `filler` / `retake` so the UI can still show why it was struck.
