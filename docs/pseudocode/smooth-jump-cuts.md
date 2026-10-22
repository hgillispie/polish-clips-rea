# Smooth jump cuts (our version)

Hide speech splices by regenerating a short span of speech across each cut. Behaviour is modelled on Descript's action ([../descript-analysis/ai-tools/smooth-jump-cuts.md](../descript-analysis/ai-tools/smooth-jump-cuts.md)). The regenerate backend is ours: [video-regenerate.md](video-regenerate.md) for the lip-synced picture, and a voice-clone TTS gated by [voice-consent.md](voice-consent.md).

## Candidates

```text
JumpCut
  key           string            # stable: composition id + left word id + right word id
  time          number            # composition time of the splice
  left_word_id, right_word_id
  seed_range    {start, end}      # composition seconds: ~last word before .. first word after

function find_jump_cuts(composition, transcript) -> JumpCut[]:
  out = []
  for each adjacent pair of kept ranges (a, b) in playback_ranges(transcript):   # transcript-model.md
    if b.source_start - a.source_end < 0.05: continue      # contiguous source = no splice
    if is_scene_boundary(composition, a.comp_end): continue  # a hard scene cut is intentional
    out.append(JumpCut(key, time=a.comp_end, ..., seed_range=(last_word(a).start, first_word(b).end)))
  return out

function smoothable(cut) = not owned_by_any_run(cut.key) and has_voice(cut.speaker)
```

## Run

```text
function run(composition, cuts, mode in {"audio_only", "video_and_audio"}, restrict_keys=null, source=null):
  run = Run(id, candidate_keys=[c.key for c in cuts if restrict_keys is null or c.key in restrict_keys],
            tau_ids=[], skip={}, status="launching", source)
  todo = sort(cuts in run.candidate_keys, by time DESC)     # reverse: later edits never shift earlier ones

  # price before launching anything
  prices = []
  for batch in chunks(todo, 20): prices += price(batch, mode)      # credits per candidate
  budget = remaining_credits()
  last_launch = -inf
  for cut, cost in zip(todo, prices):                      # one launch at a time
    if run.cancelled: break
    if cost > budget: run.skip[cut.key] = "insufficientCredits"; continue
    wait_until(last_launch + 3.0s); last_launch = now()
    cur = resolve(composition, cut.key)
    if cur is null:            run.skip[cut.key] = "boundaryUnavailable"; continue
    if cur.time != cut.time:   run.skip[cut.key] = "cutChanged"; continue
    try:
      clip = insert_regenerated_speech(cur.seed_range, text=same_words, lip_sync=(mode=="video_and_audio"),
                                       tag=run.id)
      run.tau_ids.append(clip.id); budget -= cost
    except: run.skip[cut.key] = "launchFailed"
  spawn watch(run)                                         # up to 20 concurrent watchers
  run.status = run.cancelled ? "cancelled" : "launched"

function watch(run):
  for id in run.tau_ids concurrently(20):
    poll every 1s while state(id).speech == "running" or state(id).lip_sync == "running"
    give up 10s after the job reports done without a result (grace)

function revert(run):
  for id in run.tau_ids: delete_clip(id, timeout=5s)
  run.status = "reverted"     # on error restore the list and surface it
```

## UI

- Two methods. **Review first**: list the `find_jump_cuts` results with a checkbox per cut, then run on the checked keys. **Smooth all**: run immediately.
- Before running, confirm the credit estimate. When `video_and_audio` is chosen, also confirm the voice and visual consent from [voice-consent.md](voice-consent.md).
- The results view shows one row per cut: launched, skipped with the reason, or running. It has a Revert button for the whole run.

## Errors

| Case | Behaviour |
| --- | --- |
| No consented voice for the speaker | Skip the cut (`launchFailed`) and say why |
| Cut edited during the run | `cutChanged`; never regenerate stale audio |
| Credits exhausted mid-run | Skip the remaining cuts with `insufficientCredits`; keep the ones already launched |
