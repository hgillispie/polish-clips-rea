# Use room tone on gap clips

## Keys and defaults (decompiled)

| Layer | Key | Default | Notes |
| --- | --- | --- | --- |
| Local preference (new-project default) | `Project.useRoomtoneOnGapClips` | `true` | Preferences → Advanced → "Use room tone on gap clips" |
| Project document | `settings.useRoomtoneOnGapClips` | absent (off) | Written by the Project Settings dialog ("Add room tone to new gap clips"). When the doc loads, `false` is normalized to absent |
| Gap clip | `audioSegment.enableRoomtone` | set when the clip is created | What playback actually reads. The project setting only seeds new gap clips |
| Track | `suppressRoomtone` | false | Turns room tone off for a whole track or sequence track |
| Media file | `audio.roomtoneRefId`, `audio.roomtoneTaskId`, `audio.roomtoneRequested` | absent | Links a source file to its generated room tone file |
| Room tone file | media ref of asset type `roomtone`; `audio.defaultGain` | 1 | One room tone file per source file. Its gain is shared by every gap clip that uses it |

Project actions: `SET_ROOMTONE {trackId, tauId, enableRoomtone}` (per clip, "set room tone"), the project-setting change ("change project setting - room tone"), batch enable or disable on existing gap clips ("batch enable room tone"), and room tone gain changes for a file or for a sequence.

A document migration (one schema version bump) went through every composition of projects that had the setting on and set `enableRoomtone: true` on each existing gap clip. That is how the per-clip flag was introduced (**decompiled**).

## What a gap clip is (decompiled)

In Descript's model a script track is a list of clips ("taus"). A clip is a **gap clip** when it has an audio segment with **no media file** and **no visual** (not a title, caption or other vector card). It is a stretch of silence with a duration. Gap clips are created by inserting a pause or gap in the script, by "preserve gaps on delete", by stretching, and by the agent. The creator helper sets `enableRoomtone = settings.useRoomtoneOnGapClips || undefined`. A gap clip with zero duration is ignored.

## Where the room tone comes from (decompiled + signed-in gap)

The room tone is **generated server-side per source file**. The client does not search for the quietest span itself.

1. **Request.** `POST /projects/{projectId}/roomtone` with `{audio_asset_id, audio_artifact_id}` for the source file. Poll `GET /projects/{projectId}/roomtone/{taskId}`. The result is `{roomtone_audio_asset_id, roomtone_audio_artifact_id}`.
2. **Import.** The client imports that asset as a media ref with `assetType: "roomtone"`, `source: "roomtone"`, and sets `sourceFile.audio.roomtoneRefId` to it. On failure it just clears the task id.
3. **When it is requested.** Only for audio-bearing source files that are not sequences or in-progress recordings and do not already have a task, a request or a room tone:
   - when the project setting is on and a file gets a transcript (it has a transcription language),
   - when an upload finishes (original or proxy artifact completed) and the project setting is on,
   - when the user enables room tone on one gap clip (for that clip's neighbor file),
   - when "Modify existing gap clips → Enable" runs (for every file in the media library).
   For multitrack sequences it requests one per track file.
4. **What the server does.** The UI copy says "Descript analyzes the transcribed files used in your project to add room tone to silence and gap clips". The per-clip inspector says "Fill this gap clip with room tone by analyzing the audio around it". The error catalog calls it "AI-generated background room tone synthesis" backed by a Python model service. So the server uses the transcript to find non-speech regions and **synthesizes** a room tone file from them. Whether that is a cut of the quietest span, a concatenation of several, or a fully generated noise print is not visible in the client (**signed-in gap**: download one room tone asset and compare it with its source).

### Which file a gap clip uses (decompiled)

```text
neighbors = previous non-gap clip, next non-gap clip on the same track
prefer the PREVIOUS neighbor's file if it has a room tone (or one pending)
else the NEXT neighbor's file if it has one
else (UI only) whichever neighbor is transcribed, so the inspector can offer "generate"
```

Inside a multitrack sequence, the room tone comes from the same sequence track that the clip next to the gap plays. It is skipped if that track has `suppressRoomtone`.

## How it is played: loop, fade, mix (decompiled)

When the playback or export timeline is built, each gap clip with `enableRoomtone` (and no track-level `suppressRoomtone`) is replaced by room tone clips. Otherwise it stays a silent gap. The room tone is also skipped when:

- the room tone file is missing or shorter than **2 s**, or
- the neighbor file has Studio Sound at **100 %** intensity. Studio Sound strips the noise floor, so adding room tone would reintroduce it.

**Looping.** With gap length `G` and room tone file length `R`:

```text
edge  = min(1 s, G / 2)              # fade length, and also the read offset into the file
chunk = R - 2 s                      # usable loop length
emit clips of length min(chunk, remaining) until G is covered,
each reading the room tone file from offset `edge`
```

The loops are butt-joined with no crossfade between iterations (**decompiled**; audible seams depend on the server making a loopable file, **inferred**). Clip ids are `{gapId}-rt:{n}`, flagged `isRoomtone`.

**Fades.** When room tone fades are on (the default for playback and media export), the first chunk gets a **linear** fade-in and the last chunk a **linear** fade-out, each `edge` long (≤ 1 s). Fades are stored as negative durations, which in this model means the fade extends outward into the neighbor clip (a crossfade overlap, **inferred** from the sign convention). Where the neighbor already has a fade, the shorter of the two wins. Session and DAW exports (multitrack WAV, timeline XML and similar) turn room tone fades **off**.

**Gain.**

```text
single file:   gain = neighborClip.gain × roomtoneFile.defaultGain
               if Studio Sound is partly on (0 < intensity < 1): gain ×= original-signal share of the wet/dry mix
               if a multitrack sequence's mix includes this file: gain ÷= number of non-suppressed tracks
sequence gap:  gain = neighborClip.gain × roomtoneFile.defaultGain ÷ track count
```

Room tone volume in the clip inspector changes `defaultGain` on the **room tone file**. The tooltip warns that it applies "globally to all clips which reference the same room tone file".

## UI flow (decompiled)

- **Preferences:** a boolean only. Seeds new projects.
- **Project Settings → "Add room tone to new gap clips"**: saving a change sets the project setting. If the project already has at least one non-empty gap clip, it then opens **"Modify existing gap clips"**: "Would you like to enable/disable room tone for existing gap clips as well?" with **Not now** or **Enable/Disable**. Confirming flips `enableRoomtone` on every gap clip in every composition and, when enabling, requests room tone for every file.
- **Clip inspector → Room tone section** (gap clip selected): an add or remove control, a spinner while generating, "File: {source name}", a volume slider, and "Please wait for the file to finish uploading" while the source is still uploading.
