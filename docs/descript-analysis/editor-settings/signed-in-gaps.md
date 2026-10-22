# Editor settings: signed-in gaps

Descript blocks logins from the box. These need a HAR, and two of them a downloaded file, captured by Hunter.

**HAR recipe.** In Chrome, open a **new** project. DevTools → Network → Preserve log, Disable cache. Then:

1. Upload a 2-minute talking-head clip with a few long pauses. Wait for transcription.
2. Project Settings → enable "Add room tone to new gap clips" → Save → **Enable** on the "Modify existing gap clips" prompt.
3. Insert a 3 s gap in the script. Select it and open the Room tone section in the inspector.
4. Preferences → confirm "Apply Smart transitions to new scenes" is on. Add a scene break in the script, then one from the timeline.
5. Project Settings → enable "Show wordless media in script" → Save.
6. Save as HAR **with content**. Also export a 10 s mp4 across the gap and the new scene boundary.

| # | Gap | Answered by |
| --- | --- | --- |
| 1 | Room tone server algorithm: quietest span, several spans stitched, or synthesized | `POST /projects/{id}/roomtone` + poll in the HAR. Download the room tone asset and compare it with the source |
| 2 | Room tone file length and loopability (we only know it must be ≥ 2 s; the client uses `length − 2 s` per loop) | Same asset |
| 3 | Whether the `roomtone-artifact` flag is on for the account (asset vs artifact storage) | Flags response + result ids |
| 4 | Credit or plan cost of room tone generation | Usage endpoint before and after |
| 5 | Whether the per-clip negative fade durations really overlap neighbors (crossfade) | Exported mp4 audio around the gap |
| 6 | Whether the agent's `add_scene_boundaries` also triggers Smart transitions | One Underlord turn "split this into 3 scenes", then read the scene transitions in the saved doc |
| 7 | Exact animatable property list that Smart transitions tween | Project JSON after a layout change across scenes (doc save request in the HAR) |
| 8 | Saved document shape: `settings` object, `enableRoomtone` on gap clips, transitions on boundaries | Project save or commit requests |
| 9 | Whether the wordless-media flag watcher runs on project open (and so overrides) or only on flag changes | Flags response + the doc save that follows opening |
| 10 | `DescriptWordlessMedia` font file (glyph shapes) | The font request in the HAR |
