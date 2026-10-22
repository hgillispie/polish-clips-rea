# Automatic multicam (our version)

Pick a camera (or a layout) per scene from who is speaking. Modelled on Descript's action ([../descript-analysis/ai-tools/automatic-multicam.md](../descript-analysis/ai-tools/automatic-multicam.md)). It needs a diarized transcript ([transcript-model.md](transcript-model.md)) and at least two video tracks.

## Settings

```text
MulticamSettings
  max_word_gap            = 3.0   # s
  scene_min / scene_max   = 3 / 45  (cutaways: occasional max 30, frequent max 10, none max inf)
  break_duration          = 3.0
  start_buffer/end_buffer = 0.3 / 0.3
  merge_reactions         = false
  merge_silences          = true
  jump_cut_scene_duration = 1.5
  min_jump_cut_gap        = 0.3
  min_scene_contribution  = 0     # agent path: 0.5
  split_long / merge_short = true / true   # agent path: false / false
  rules                   Rule[]  # see below; "active speaker only" = one rule {show: active_speakers, maxSpeakers: 1}
```

## Steps

```text
function multicam(comp, transcript, tracks, settings, camera_assignments=null, layout_pack=null):
  require has_video(comp)                     else fail "no video"
  speakers = speakers_with_words(transcript); require len(speakers) >= 2
  cams = video_tracks(comp);                  require len(cams) >= 2
  mapping = assign_cameras(speakers, cams, camera_assignments)
  require count(mapping) >= 2

  # 1. contributions
  contribs = []
  for w in kept_words(transcript):
    c = contribs.last
    if c and c.speaker == w.speaker and w.start - c.end <= settings.max_word_gap: c.end = w.end
    else contribs.append(Contribution(w.speaker, w.start, w.end))

  # 2. 0.5 s buckets of active speakers
  buckets = for t in range(0, comp.duration, 0.5):
              {s for c in contribs if c.start - start_buffer <= t < c.end + end_buffer}

  # 3. scenes
  scenes = group consecutive buckets with the same active set
  for s in scenes: s.type = silence if empty
                           else reaction if duration < 2 and differs from neighbours
                           else monologue if one speaker else back_and_forth
  if merge_silences: fold silence into the previous scene
  if merge_reactions: fold reactions into the surrounding scene
  if split_long: split scenes > scene_max at word gaps >= break_duration (else at scene_max)
  if merge_short: merge scenes < scene_min into the neighbour with more shared speakers

  # 4. rules
  for s in scenes:
    matches = [r for r in rules if r.if matches s]
    top = max priority in matches; picked = [r in matches with priority == top]
    show = union of picked.then targets; limit = min(r.then.maxSpeakers for r in picked if set)
    s.cameras = first `limit` of [mapping[sp] for sp in show]

  # 5. apply in one commit
  if layout_pack: copy pack media; for s: s.layout = best_layout(pack, n_script_layers, len(s.cameras))
  write scene boundaries + per-scene track visibility (or layout) ; commit "automatic multicam"
  if agent: delete scenes < 0.5 s ; commit "clean up scenes"
  return summary(mapping, settings)

function assign_cameras(speakers, cams, explicit):
  if explicit: return {sp: cam where cam.name contains explicit[sp]}
  m = {sp: cam where normalize(cam.name) == normalize(sp.name)}
  fill unassigned speakers into unused cams in order
  then speakers owning paragraphs with >= 20 chars, if still unmapped
```

## Errors

no video · fewer than 2 speakers · fewer than 2 video tracks · fewer than 2 assigned cameras · named speaker or track not found. Fail before writing anything.
