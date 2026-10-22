# Automatic multicam

Switches between camera tracks (and layouts) by who is speaking. Sources (all **decompiled**):

- chunk 9105: the panel (module "Automatic multicam")
- chunk 5433: the UI defaults and the internal action
- the app chunk: the agent tool `automatic_multicam`, the worker client and the scene cleanup

It was not run in Hunter's capture (flag `magic-multicam` is true for him). Pseudocode: [../../pseudocode/automatic-multicam.md](../../pseudocode/automatic-multicam.md).

## Panel

- **Name and copy.** "Automatic multicam": "Automatically pick layouts & cameras to show active conversations".
- **Gates.** Paywall `aiEffectAutomaticMulticam` (usage feature `automatic_multicam`). The preset is in the "needs video" set. The panel shows a Stop button.
- **Parameters:**

| Key | Label | Options |
| --- | --- | --- |
| `style` | Style | Automatic; Show only active speaker |
| `cutawaysType` | Cutaways | Occasional (scene max 30 s, break 3 s); Frequent (max 10 s, break 3 s); None (max ∞) |
| `cameraSetup` | Camera setup | A speaker → camera track mapping, auto-filled |
| `templateProjectDetails` | Use layout pack | Optional layout pack project |

"Show only active speaker" maps to rules that cap the shown speakers at 1 (**inferred** from the rule schema).

## Settings and defaults

| Setting | UI default | Agent tool default |
| --- | --- | --- |
| `maxWordGap` (s, merge words into one contribution) | 3 | 3 |
| `sceneMinDuration` / `sceneMaxDuration` (s) | 3 / 45 | 3 / 45 |
| `breakDuration` (s) | 3 | 3 |
| `startBuffer` / `endBuffer` (s) | 0.3 / 0.3 | 0.3 / 0.3 |
| `mergeReactions` | false | false |
| `mergeSilences` | true | true |
| `jumpCutSceneDuration` (s) | 1.5 | 1.5 |
| `minJumpCutGap` (s) | 0.3 | 0.3 |
| `minSceneContributionDuration` (s) | 0 | 0.5 |
| `shouldSplitLongScenes` / `shouldMergeShortScenes` | true / true | false / false |

## Algorithm

1. **Contributions.** Walk the aligned words. Group consecutive words while the speaker stays the same and the gap is at most `maxWordGap`.
2. **Buckets.** Sample the timeline in 0.5 s buckets. Each bucket holds the contributions active in it, widened by the start/end buffers.
3. **Scene typing.** Classify each run of buckets:
   - `monologue`: one speaker
   - `back_and_forth`: speakers alternating
   - `reaction`: a short interjection, under 2 s
   - `silence`
   - Optional passes: merge reactions or silences into neighbors, split scenes longer than the max, merge scenes shorter than the min.
4. **Rules.** Each scene picks which cameras to show:

```text
Rule
  priority   number
  if         {sceneType?, hasSpeaker?, allSpeaking?, sceneDuration?{min,max}, hasJumpCut?}
  then       {show: active_speakers | all_speakers | specific_speakers | non_active_speakers,
              speakers?: string[] (may include "__active__"), maxSpeakers?}
```

   - Only rules at the **highest matching priority** apply.
   - Rules that share that priority add together, and the smallest `maxSpeakers` wins.
5. **Camera setup.**
   - The mapping comes from `cameraAssignments`, matched by a substring of the track name.
   - Otherwise it is automatic: a track whose name matches a speaker name maps to that speaker.
   - Unassigned speakers fill the empty camera tracks in order.
   - Last, speakers from paragraphs with at least 20 characters of text are assigned.
6. **Apply.** This runs in a worker ("Multicam client provider").
   - **Without a layout pack**, `createScenes` writes scene boundaries and per-scene track visibility.
   - **With a pack**, `createScenesAndApplyLayouts`:
     1. Copies the pack's media into the project (`copyMediaAssetsFromProject`).
     2. Picks a layout for each scene by the number of script and camera layers. It prefers `layoutType: multicam` and layouts with same-sized script layers.
   - Progress is reported as a percentage. One commit, message "automatic multicam".

## Errors

No video; fewer than 2 speakers; fewer than 2 video tracks; fewer than 2 assigned cameras; a named speaker or track was not found.

## Agent tool `automatic_multicam`

- It uses the agent defaults above.
- After applying, it deletes scenes shorter than 0.5 s (telemetry `scene_boundary_deleted`) in a second commit, "Clean up scenes".
- The tool result is a text summary of the camera assignments and the settings used.
