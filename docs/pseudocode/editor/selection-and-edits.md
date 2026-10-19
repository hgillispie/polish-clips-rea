# Selection and edits

Three timeline edits, plus the transcript link. Ripple, roll, and slip are the usual NLE meanings, adopted here as our behaviour. They are not a claim about how Descript implements those gestures (**inferred** only as common editor vocabulary).

Nondestructive ignore from [../transcript-model.md](../transcript-model.md) still wins over hard delete. Striking a word sets `ignored`. It does not remove the `Word`.

## Definitions

```text
Ripple
  Change the composition-clock length of a clip (trim the start, trim the end,
  or remove a middle span). Every later clip on the same track moves by the
  same delta. Clips that share link_group on other tracks move too.
  Clips that start before the edit point and do not share the group stay put.

Roll
  Move the boundary between two adjacent clips on one track.
  The left clip's duration grows by dt and the right clip's start and source_in
  shift so its end stays fixed. Later clips do not move.
  The two clips must be adjacent (gap < 1 ms) and on the same track.

Slip
  Change what source media is visible without moving the clip on the timeline.
  Add dt to source_in and source_out. start_seconds and duration_seconds stay.
  Clamp so source_in >= 0 and source_out <= media.duration.
```

```text
function ripple_trim_end(clip, new_duration):
  dt = new_duration - clip.duration_seconds
  clip.duration_seconds = new_duration
  clip.source_out = clip.source_in + new_duration * clip.speed
  shift_later(clip, dt)

function shift_later(edited, dt):
  point = edited.start_seconds
  for clip in all clips:
    same_track = clip.track_id == edited.track_id and clip.start_seconds > point
    linked = edited.link_group is not null and clip.link_group == edited.link_group
      and clip.start_seconds > point
    if same_track or linked:
      clip.start_seconds += dt

function roll(left, right, dt):
  if not adjacent(left, right):
    fail "roll needs two adjacent clips"
  if left.duration_seconds + dt <= 0 or right.duration_seconds - dt <= 0:
    fail "roll would erase a clip"
  left.duration_seconds += dt
  left.source_out += dt * left.speed
  right.start_seconds += dt
  right.source_in += dt * right.speed
  right.duration_seconds -= dt

function slip(clip, dt):
  media = project.media.by_id(clip.media_id)
  next_in = clip.source_in + dt
  next_out = clip.source_out + dt
  if next_in < 0 or next_out > media.duration_seconds:
    fail "slip leaves the source"
  clip.source_in = next_in
  clip.source_out = next_out
  # Transcript link: word_ids whose source interval still overlaps
  # [source_in, source_out] stay; others drop off the link.
  relink_words(clip)
```

Roll and slip do not change `Word.ignored`. They change which source interval the clip shows.

## Transcript selection

```text
function select_words(transcript, anchor_id, focus_id) -> Selection:
  # Same bounds as clip-cut.md selection_bounds.
  return Selection(anchor_word_id, focus_word_id)

function selection_to_timeline(composition, selection) -> ClipRange | null:
  words = span(transcript, selection)
  t0 = words[0].start_seconds
  t1 = words.last.end_seconds
  clip = the video or audio clip whose transcript_link.word_ids intersect words
  if clip is null:
    return null
  # Source clock equals composition clock while the seeded clip starts at 0
  # with source_in 0 and speed 1. Otherwise map:
  comp_t0 = clip.start_seconds + (t0 - clip.source_in) / clip.speed
  comp_t1 = clip.start_seconds + (t1 - clip.source_in) / clip.speed
  return ClipRange(clip.id, comp_t0, comp_t1)
```

The timeline highlights that range. The inspector shows the clip. The transcript panel scrolls to the anchor.

## Ignore from the transcript

```text
function ignore_words(composition, transcript, word_ids, reason):
  for id in word_ids:
    word = transcript.words.by_id(id)
    word.flags.ignored = true
    if reason == "filler":
      word.flags.filler = true
    if reason == "retake":
      word.flags.retake = true
  apply_ignores_to_timeline(composition, transcript)

function apply_ignores_to_timeline(composition, transcript):
  # Rebuild skip ranges on every clip linked to this transcript,
  # then ripple-close those ranges so playback has no gap.
  for clip in clips_linked(composition, transcript.id):
    clip.skip_ranges = []
    for word in transcript.words:
      if word.id not in clip.transcript_link.word_ids:
        continue
      if not word.flags.ignored:
        continue
      (a, b) = word_to_comp(clip, word)
      clip.skip_ranges.append(SkipRange(a, b, reason_of(word), [word.id]))
    close_skips(clip)

function close_skips(clip):
  # Turn each skip into a ripple that pulls the tail of THIS clip forward
  # by splitting the clip. Source clocks of the pieces stay on the media.
  # Later linked clips shift by the total removed time.
  pieces = []
  cursor = clip.start_seconds
  for keep in kept_comp_ranges(clip):     # complement of skip_ranges
    piece = copy(clip)
    piece.start_seconds = cursor
    piece.duration_seconds = keep.duration
    piece.source_in = comp_to_source(clip, keep.start)
    piece.source_out = comp_to_source(clip, keep.end)
    piece.skip_ranges = []
    pieces.append(piece)
    cursor += keep.duration
  removed = clip.duration_seconds - sum(p.duration_seconds for p in pieces)
  replace clip on its track with pieces
  shift_later_excluding_pieces(clip, -removed)
  rebuild_caption_cues(composition)        # captions.md from non-ignored words
```

Restore clears `ignored` on those words and runs `apply_ignores_to_timeline` again from the original single clip. To make that possible, the composition keeps `source_clip` identity: pieces created by `close_skips` share `split_from = original clip id`, and restore merges pieces that share `split_from` back into one clip before recomputing. If the operator has rolled or slipped a piece, restore refuses that word group and asks for an explicit confirm, because the source window is no longer the one ignore captured.

Playback of a clip with skip ranges **before** `close_skips` also skips the audio and video (preview). `close_skips` is what makes the timeline show the tightened cut. Run it after filler removal, retake removal, and manual strikes.

## Caption track

`rebuild_caption_cues` runs [../captions.md](../captions.md) `build_captions` on the transcript and writes the cues onto the linked caption clip. Style id is unchanged. Ignored words are absent from the cues, so burn-in cannot paint them.

## Errors

| Case | Behaviour |
| --- | --- |
| Selection word from another transcript | Fail the selection |
| Ripple that would push a clip to `start < 0` | Clamp that clip to 0 and shorten it; record the clamp |
| Roll of clips on different tracks | Fail |
| Slip with no media | Fail |
| Restore after a manual roll | Refuse until the operator confirms; do not guess a new source window |
| Empty result after closing skips | Leave a zero-length placeholder off the timeline and report "no audible words" |

No 402.
