# Descript editor settings: room tone, Smart transitions, wordless media

Clean-room notes on three toggles in Descript's settings, from the public `web.descript.com` bundles of build `react19/9a29d61183bce669600a9dd9a1f8588d708becac`. The settings UI was not in the 41 chunks we had, so on 2026-10-22 we pulled the remaining 104 chunks listed in that build's webpack runtime (all public, no login). The two settings screens are in chunks `1707` (app Preferences) and `6552` (editor, including the Project Settings dialog). Both were unpacked with Wakaru 1.14.0 `--unpack=strict`. The behavior lives in chunks `88`, `3549`, `5708`, `760`, `1445`, the app chunk, and the `nme-timeline` worker. Recovered modules stay on the research box. This folder has our descriptions only.

Evidence tags: **decompiled** (read in a recovered module, call sites traced), **static-bundle** (string or CSS seen, not traced), **inferred** (our conclusion), **signed-in gap** (needs a HAR; see [signed-in-gaps.md](signed-in-gaps.md)).

| File | Covers |
| --- | --- |
| [room-tone.md](room-tone.md) | "Use room tone on gap clips": keys, defaults, what a gap clip is, where the room tone file comes from, how it is looped, faded and mixed |
| [smart-transitions.md](smart-transitions.md) | "Apply Smart transitions to new scenes": what triggers it, the transition it adds, duration and easing, how matching layers morph across the cut |
| [wordless-media.md](wordless-media.md) | "Show wordless media in script" (Beta): which spans count, how they become waveform glyphs inside script text, editing rules |
| [signed-in-gaps.md](signed-in-gaps.md) | What still needs a signed-in capture, with a HAR recipe |

Pseudocode for our versions: [../../pseudocode/editor-settings/](../../pseudocode/editor-settings/).

## Where each toggle lives (decompiled)

| Toggle (UI text) | Preferences (app-wide default) | Project Settings dialog (per project) | Stored in the project document |
| --- | --- | --- | --- |
| Use room tone on gap clips | Yes. Local pref `Project.useRoomtoneOnGapClips`, default **true** | Yes. Shown as "Add room tone to new gap clips" (`roomtone-toggle`) | `settings.useRoomtoneOnGapClips` (optional bool; `false` is stored as absent), plus a per-gap-clip `audioSegment.enableRoomtone` |
| Apply Smart transitions to new scenes | Yes. Local pref `Application.applySmartTransitions`, default **undefined, read as true** | **No.** App-wide only | Nothing stored as a setting. The result is ordinary scene transitions whose effect type is `com.descript.smartTransition` |
| Show wordless media in script (Beta) | Yes. Local pref `Project.showWordlessMedia`, default **false** (`wordless-media-switch`) | Yes (`wordless-media-toggle`) | `settings.wordlessMediaEllipses` (optional bool) |

The Preferences entries only set what new projects start with. The copy says so: "If on, new projects will … This can be overridden in each project's settings." New projects are created with `{automaticallyLevelClips, useRoomtoneOnGapClips, wordlessMediaEllipses, syncProjectName: true}` read from the local prefs. The project-level default object has `useRoomtoneOnGapClips: undefined` and `wordlessMediaEllipses: undefined`, so older projects read as **off** for both.

The Project Settings dialog has a "Set as default for all new projects" checkbox. It appears only when something changed, and it writes the same local prefs. "Save changes" is disabled until a value differs.

Feature flags:

| Toggle | Flag | Default | Effect |
| --- | --- | --- | --- |
| Room tone | `roomtone-artifact` | false | Server writes the generated room tone as an artifact on the original asset instead of as its own asset. Storage only, no UX change |
| Smart transitions | none found | n/a | No flag. The auto-add runs on any project, but the cross-scene morph is only computed for "storyboard" (new document model) compositions with video metadata |
| Wordless media | `wordless-media-ellipses` | false | When it resolves **true**, the app pushes `SET_WORDLESS_MEDIA {on: true}` for the open project, unless that project explicitly stored `false`. It is a rollout lever that turns the feature on for people who never touched it |
| Wordless media | `wordless-media-ellipses-kill-switch` | true | Serving `false` makes the watcher push `SET_WORDLESS_MEDIA {on: undefined}`, which clears the setting (feature off) on any project that did not explicitly store `false`. So it is a real kill switch, even for projects that had it on. It does not hide the toggle (**decompiled**; whether the watcher fires on project open or only on flag change is a **signed-in gap**) |
| Wordless media (agent) | `underlord-wordless-media-no-match` | false | Underlord rejects text anchors that only match across wordless spans (AVE-4649, created 2026-09-14) |

Both Room Tone and the project-settings area have their own owner surfaces in the error-reporting catalog: "Room Tone: AI-generated background room tone synthesis for audio continuity", "RoomToneBackend: model python code and deployment", and "ProjectSettings: auto-leveling, room tone, wordless media display preferences" (**static-bundle**).
