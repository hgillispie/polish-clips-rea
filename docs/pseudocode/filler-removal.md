# Filler removal

Mark filler words and set `ignored`. Leave the `Word` in the transcript so the operator can restore it. Playback and default captions skip ignored words via [transcript-model.md](transcript-model.md) `kept_ranges`.

The web client's action id for this edit is `remove-filler-words`, credit key `remove_filler_words` → `script_editing` (**static-bundle**). That id is not a field on the public agent job. This file still sets `ignored` locally.

## Input / output

```text
input:
  transcript          Transcript        # alignment should be "word"
  options
    lexicon           FillerLexicon     # default English lexicon below
    ignore            boolean           # default true
    extra_phrases     string[]          # operator additions, already normalized
output:
  transcript          # same ids; flags updated
  report
    marked_word_ids   string[]
    skipped_reason    string | null     # set when alignment is "cue"
```

## Default lexicon (English)

Single tokens, compared after `normalize`:

```text
um, uh, uh-huh, er, ah, hmm, mm, mhm
```

Multi-word phrases, matched as a span of consecutive non-ignored tokens:

```text
you know, i mean, sort of, kind of
```

`like` and `so` are **not** in the default single-token list. They are usually content words. An operator can add them through `extra_phrases`. This caution is a product choice (**inferred** from how filler buttons false-positive), not a Descript rule.

`normalize(text)`: lowercase, strip leading/trailing punctuation, collapse internal hyphens to nothing (`uh-huh` → `uhhuh` for the key, while display `text` stays as spoken).

## Algorithm

```text
function remove_fillers(transcript, options) -> (transcript, report):
  if transcript.alignment != "word":
    return transcript, report(marked=[], skipped_reason="cue alignment; split tokens first")

  keys = options.lexicon.single ∪ options.extra_phrases
  phrases = options.lexicon.phrases
  marked = []

  i = 0
  while i < transcript.words.length:
    word = transcript.words[i]
    if word.flags.ignored:
      i += 1
      continue

    phrase = match_phrase(transcript.words, i, phrases)
    if phrase is not null:
      for w in phrase:
        mark(w, marked, options.ignore)
      i += phrase.length
      continue

    if normalize(word.text) in keys and not false_start_only(word):
      mark(word, marked, options.ignore)
    i += 1

  return transcript, report(marked_word_ids=marked, skipped_reason=null)

function mark(word, marked, ignore):
  word.flags.filler = true
  if ignore:
    word.flags.ignored = true
  marked.append(word.id)

function match_phrase(words, start, phrases) -> Word[] | null:
  # Try longest phrase first.
  # Only consecutive words with no ignored word and a gap <= 0.4s between them.
  for phrase in phrases sorted by length descending:
    span = words[start : start + phrase.length]
    if span.length != phrase.length:
      continue
    if any word in span is ignored:
      continue
    if any adjacent gap inside span > 0.4:
      continue
    if [normalize(w.text) for w in span] == phrase.tokens:
      return span
  return null
```

`false_start_only` rejects a token whose normalized form is empty after stripping punctuation. It does not try to be a language model.

Idempotent: running twice does not create duplicate ids in the report beyond the same words, and does not clear a manual `ignored` on a non-filler.

## Restore

```text
function restore_fillers(transcript, word_ids | "all"):
  targets = all words with flags.filler if word_ids == "all" else those ids
  for word in targets:
    word.flags.ignored = false
    # flags.filler stays true
  return transcript
```

## Errors

| Case | Behaviour |
| --- | --- |
| Empty transcript | Return an empty report. Not an error |
| `alignment == "cue"` | Do not guess which token inside a cue is the filler. Return `skipped_reason` |
| Unknown language | Run the English lexicon only when `language` starts with `en`. Otherwise return `skipped_reason="no lexicon"` unless `extra_phrases` is non-empty, in which case apply only those phrases |

No HTTP 402 on this path. It is local.

## Descript API option

There is no filler endpoint (static). A prompt can ask Underlord to do it. Official example wording is destructive ("remove all filler words"). Our preferred prompt asks for a reversible strike and is **unverified**:

```text
Strike through filler words such as "um" and "uh" so they do not play.
Keep them in the transcript so they can be restored. Do not delete the words.
```

After the job, `POST /export/transcript` as `txt` and compare with the source. If the fillers are gone, the API backend hard-deleted and cannot satisfy ignore semantics. Record that on the fixture and keep the open stack as the editor of record. Job mechanics: [underlord-agent-job.md](underlord-agent-job.md).

## Build options

| Option | Notes |
| --- | --- |
| Local lexicon (this file) | Default. Deterministic, reversible, no credits |
| Local lexicon plus a small classifier later | Only if fixture review shows too many misses. Still writes the same flags |
| Underlord prompt | Black box. Spends AI credits (402 if empty). Treat the result as a new project state, then re-import the transcript if you need flags |
