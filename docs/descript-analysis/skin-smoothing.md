# Descript: skin smoothing

Rewritten from the public web client, build `react19/9a29d61183bce669600a9dd9a1f8588d708becac` (2026-10-19). The previous revision of this file was help text only.

Wakaru module **351916** (decompiled). Cloud-spec strings are **static-bundle** in chunk 88 `88.fc0ea62a7f115f3adca9.js`. The module body is not vendored here.

## Identity

| Item | Value | Tag |
| --- | --- | --- |
| UI category | Special | decompiled |
| Media flag | `beautifyRequested` | static-bundle |
| Agent field | `skinSmoothing` boolean. `true` enables defaults. `false` disables. The agent schema does **not** expose the slider vector | static-bundle |
| Credits | 5 AI credits **per file the first time** it is applied to that file | static-bundle agent copy |
| Credit key | `skin_smoothing` → `ai_effects` | static-bundle |
| HD six-pack | Not a member. Eye Contact, background blur/removal, portrait, uplight, and speaker focus have `com.descript.*` ids. Skin smoothing's binding in the minified map is `mo.WaC`. No `com.descript.skinSmoothing` string was recovered | static-bundle |
| Cloud POST | Not one of `eye_gaze_correction`, `background_removal`, `face_tracking`, `lip_sync`, `speech_enhancement` | static-bundle absence |

Eye Contact is `com.descript.eyeContact` and `eyeContactRequested`. It is a different effect. See [eye-contact.md](eye-contact.md).

## Parameter vector (decompiled module 351916)

Ordered `defaultPreset`:

`[0.4, 3, 0.0212, Regions, 1, 0.3, 0.3, 2.5]`

| Index | Control | Default |
| --- | --- | --- |
| 0 | Base strength | `0.4` |
| 1 | Radius | `3` |
| 2 | Edge feather | `0.0212` |
| 3 | Mask area | `Regions` (the other value is `WholeFace`) |
| 4 | Forehead multiplier | `1` |
| 5 | Cheeks multiplier | `0.3` |
| 6 | Laugh-lines multiplier | `0.3` |
| 7 | Under-eyes multiplier | `2.5` |

The pack audit names this module's minified parameter-index symbols `EX` and `y0`. Those identifiers are not re-declared here, and the module source is not in git. Implementations use the index order in the table. The unit of edge feather `0.0212` is unlabeled in the summary; treating it as a fraction of the face box is **inferred**.

Region multipliers scale the base strength. `WholeFace` ignores the four multipliers and uses one mask. That split matches the two mask-area values (**decompiled** names, **inferred** blend rule).

## Credits and cache

The agent sentence charges 5 AI credits per file on first apply. It does not say a later strength edit on the same file is charged again. Polish Clips charges once per source file when `beautifyRequested` first flips on, and does not charge for a parameter edit after that (**inferred** from "the first time").

Help-page limitations (small faces, three or more people, hats, glasses, hands, coverings, turned heads, low light, non-faces) are **static-help** from the help center, not strings in module 351916. The bundle does not publish a faceprint claim. Do not store a face embedding.

## Render

Local soften on the face mask after the flag is set. No background-mask artifact is required. Pseudocode: [../pseudocode/skin-smoothing.md](../pseudocode/skin-smoothing.md).
