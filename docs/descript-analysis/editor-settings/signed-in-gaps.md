# Editor settings: signed-in gaps

**Status 2026-10-22.** Hunter's signed-in capture closed or narrowed most rows. The results are in the **Result** column; *open* means the capture did not answer it. Tags: **observed-network**, **decompiled**, **inferred**.

Descript blocks logins from the box. These need a HAR, and two of them a downloaded file, captured by Hunter.

**HAR recipe.** In Chrome, open a **new** project. DevTools → Network → Preserve log, Disable cache. Then:

1. Upload a 2-minute talking-head clip with a few long pauses. Wait for transcription.
2. Project Settings → enable "Add room tone to new gap clips" → Save → **Enable** on the "Modify existing gap clips" prompt.
3. Insert a 3 s gap in the script. Select it and open the Room tone section in the inspector.
4. Preferences → confirm "Apply Smart transitions to new scenes" is on. Add a scene break in the script, then one from the timeline.
5. Project Settings → enable "Show wordless media in script" → Save.
6. Save as HAR **with content**. Also export a 10 s mp4 across the gap and the new scene boundary.

| # | Gap | Answered by | Result |
| --- | --- | --- | --- |
| 1 | Room tone server algorithm: quietest span, several spans stitched, or synthesized | `POST /projects/{id}/roomtone` + poll in the HAR. Download the room tone asset and compare it with the source | **Closed in part (observed-network).** `POST /v2/projects/{id}/roomtone {audio_asset_id, audio_artifact_id}` returns a task `{id, state: queued\|done, result: {roomtone_audio_asset_id, roomtone_audio_artifact_id}}`. The client polls `GET …/roomtone/{taskId}` about once a second; `done` arrived after about 8–9 s. A repeat request for the same audio comes back `done` at once (cached). The server algorithm itself is still not visible |
| 2 | Room tone file length and loopability (we only know it must be ≥ 2 s; the client uses `length − 2 s` per loop) | Same asset | **Closed (observed-network).** The result is a separate room tone media ref about **30 s** long, looped by the client as documented |
| 3 | Whether the `roomtone-artifact` flag is on for the account (asset vs artifact storage) | Flags response + result ids | **Closed (observed-network).** `roomtone-artifact` resolved to **false** (asset storage). The task result still carries both `roomtone_audio_asset_id` and `roomtone_audio_artifact_id` |
| 4 | Credit or plan cost of room tone generation | Usage endpoint before and after | *Open.* No usage endpoint was read |
| 5 | Whether the per-clip negative fade durations really overlap neighbors (crossfade) | Exported mp4 audio around the gap | *Open.* No export was captured |
| 6 | Whether the agent's `add_scene_boundaries` also triggers Smart transitions | One Underlord turn "split this into 3 scenes", then read the scene transitions in the saved doc | **Closed (observed-network).** The agent's `add_scene_boundaries` and a manual "Split scene" (`ADD_CARD_BOUNDARY_AT_TIME_OFFSET`) both wrote **no** Smart transition. The only transition came from an explicit `update_scene_properties` call: `transitionProperties {headOrTailType: head, effect: {effectType: crossfade}, duration: 0.5}`, stored as a `videoFades` entry of type `com.descript.crossFadeTransition`. Hunter's `applySmartTransitions` local pref is not in the network capture, so "not added" may just mean his pref is off (*open*) |
| 7 | Exact animatable property list that Smart transitions tween | Project JSON after a layout change across scenes (doc save request in the HAR) | *Open.* No layout change across scenes was captured |
| 8 | Saved document shape: `settings` object, `enableRoomtone` on gap clips, transitions on boundaries | Project save or commit requests | **Closed (observed-network).** Commits are `POST /v2/projects/{id}/collab/commits` with `{edit: {actionType, message}, graph: {delta}}`. The initial commit's `settings` includes `automaticallyLevelClips`, `useRoomtoneOnGapClips` and `wordlessMediaEllipses: false`. Room tone tasks appear as `EDITOR/EFFECT/ADD_ROOMTONE_TASK_ID` / `REMOVE_ROOMTONE_TASK` commits |
| 9 | Whether the wordless-media flag watcher runs on project open (and so overrides) or only on flag changes | Flags response + the doc save that follows opening | **Narrowed.** The project's initial settings had `wordlessMediaEllipses: false` stored explicitly, so the flag watcher could not override it whatever its timing. Hunter then turned the toggle on in the UI (prompt B6 in [../underlord/prompt-catalog.md](../underlord/prompt-catalog.md)) |
| 10 | `DescriptWordlessMedia` font file (glyph shapes) | The font request in the HAR | *Open.* No `DescriptWordlessMedia` font request is in the capture: only Booton, Roboto, Roboto Condensed and Inter webfonts loaded. The signed CSS uses `font-family: DescriptWordlessMedia` in two rules: the script's wordless-run decoration, and the tag decoration at 16 px. Neither CSS chunk we hold has an `@font-face` for it, and the JS never names it, so the font file comes from a global stylesheet or font loader we did not fetch (*open*). The wordless run also has a 3 s, 20-step loading animation while it transcribes (static-bundle CSS) |
