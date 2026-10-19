# Retake removal

Find an earlier attempt of a line and ignore it, keeping the later take. Same `ignored` flag as fillers, plus `retake` and `retake_group_id`, so a restore brings the abandoned take back without un-ignoring fillers inside it unless those are restored separately.

## Input / output

```text
input:
  transcript     Transcript     # word alignment
  options
    pause_seconds        number    # default 0.45; gap that splits utterances
    window_seconds       number    # default 30; how far back a retake may refer
    similarity_threshold number    # default 0.72; token Jaccard
    min_tokens           integer   # default 3; shorter spans are not retakes
    ignore               boolean   # default true
output:
  transcript
  report
    groups: { id, abandoned_word_ids, kept_word_ids, score }[]
```

## Utterances

```text
Utterance
  words            Word[]
  start_seconds    number
  end_seconds      number
  speaker_id       string | null
  tokens           string[]     # normalize(word.text) for words that are not fillers

function utterances(transcript, pause_seconds) -> Utterance[]:
  groups = []
  current = []
  for word in transcript.words:
    if current is empty:
      current = [word]
      continue
    gap = word.start_seconds - current.last.end_seconds
    speaker_changed = word.speaker_id != current.last.speaker_id
      and word.speaker_id is not null
      and current.last.speaker_id is not null
    if gap > pause_seconds or speaker_changed:
      groups.append(to_utterance(current))
      current = [word]
    else:
      current.append(word)
  if current is not empty:
    groups.append(to_utterance(current))
  return groups
```

Filler-flagged tokens are removed from `tokens` before comparison so "um we should ship" matches "we should ship". They stay in `words` and, if already ignored, remain ignored.

## Algorithm

Keep the **last** similar utterance. Mark the earlier one as the retake. Do not compare across speakers when both sides have a `speaker_id`.

```text
function remove_retakes(transcript, options) -> (transcript, report):
  if transcript.alignment != "word":
    return transcript, report(groups=[], skipped_reason="cue alignment")

  utts = utterances(transcript, options.pause_seconds)
  groups = []
  suppressed = set()          # utterance indexes already marked

  for i, later in enumerate(utts):
    if i in suppressed:
      continue
    if later.tokens.length < options.min_tokens:
      continue
    best = null               # (index, score)
    for j in range(i - 1, -1, -1):
      earlier = utts[j]
      if later.start_seconds - earlier.end_seconds > options.window_seconds:
        break
      if j in suppressed:
        continue
      if speakers_differ(earlier, later):
        continue
      if earlier.tokens.length < options.min_tokens:
        continue
      score = jaccard(earlier.tokens, later.tokens)
      score = max(score, prefix_restart_score(earlier.tokens, later.tokens))
      if score >= options.similarity_threshold and (best is null or score > best.score):
        best = (j, score)
    if best is null:
      continue
    j, score = best
    gid = new_id()
    for word in utts[j].words:
      word.flags.retake = true
      word.flags.retake_group_id = gid
      if options.ignore:
        word.flags.ignored = true
    suppressed.add(j)
    groups.append({
      id: gid,
      abandoned_word_ids: [w.id for w in utts[j].words],
      kept_word_ids: [w.id for w in later.words],
      score: score
    })

  return transcript, report(groups=groups)

function jaccard(a, b) -> number:
  if a is empty and b is empty:
    return 0
  return |set(a) ∩ set(b)| / |set(a) ∪ set(b)|

function prefix_restart_score(earlier, later) -> number:
  # False start: later begins with the first min_tokens of earlier,
  # or earlier is a prefix of later ("so I think" / "so I think we should").
  n = min(len(earlier), len(later), options.min_tokens)
  if earlier[:n] == later[:n]:
    return len(common_prefix(earlier, later)) / max(len(earlier), len(later))
  return 0

function speakers_differ(a, b) -> boolean:
  return a.speaker_id is not null and b.speaker_id is not null
     and a.speaker_id != b.speaker_id
```

A chain of three attempts collapses pairwise: take 1 is suppressed when take 2 matches it, then take 2 is suppressed when take 3 matches it. Take 3 remains. Because suppressed utterances are skipped as the "later" side only after they were already used, walk forward as written; when `i` itself was suppressed, `continue` so an abandoned middle take is not also treated as the keeper.

Apply fillers **before** retakes so filler tokens are already flagged and excluded from `tokens`.

## Restore

```text
function restore_retake(transcript, group_id):
  for word in transcript.words:
    if word.flags.retake_group_id == group_id:
      word.flags.ignored = false
      # flags.retake stays true until the operator clears the group
  return transcript
```

Clearing the group sets `retake=false` and `retake_group_id=null` on those words and does not change `filler`.

## Errors

| Case | Behaviour |
| --- | --- |
| Cue alignment | Skip with `skipped_reason`. Do not mark whole caption lines as retakes |
| No speaker labels | Compare by text only. Accept more false positives; the UI lists each group for review |
| Overlapping groups | An ignored word may be both `filler` and `retake`. Restore of one flag path must not clear the other flag |

Local only: no 402.

## Descript API option

No retake schema (static). Unverified prompt, sent through [underlord-agent-job.md](underlord-agent-job.md):

```text
Remove retakes and false starts. When a line is attempted more than once,
keep the last complete take and drop the earlier attempts. Leave filler
words that are not part of a retake alone.
```

If the open-stack editor is the source of truth, do not also send this prompt: the two edits will not share `retake_group_id`s. Use the API path only when the whole polish runs as one Underlord job ([polish-pipeline.md](polish-pipeline.md) backend `descript_api`).

## Build options

| Option | Notes |
| --- | --- |
| Jaccard + prefix restart (this file) | Default. Explainable scores in the report |
| Embedding similarity later | Replace `jaccard` only. Same flags and report shape |
| Underlord prompt | Black box, credit-metered, no group ids to restore |
