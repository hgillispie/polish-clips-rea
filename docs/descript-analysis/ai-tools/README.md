# Descript AI Tools panel: catalog

The AI Tools menu (the sparkle button, then group tabs) in signed build `react19/a7c779e…`. The item table is in chunk 8211 and the per-action panels are in chunk 9105 (**decompiled**).

Every item has an `id`, a label, a `getDisabledMessage` (no media, no transcript, no video, and so on), an `execute` that dispatches one Redux action, a `staticInfo` card (title, subtitle, image) and a `paywallId` (feature-access key). Most items open a parameter panel through `SET_AI_ACTIONS_PROMPT {presetId, …}`, and the panel's Run button sends the action. A few dispatch an editor action directly.

| Group | Item | `execute` dispatches | Preset / panel | Paywall id | Our doc |
| --- | --- | --- | --- | --- | --- |
| Write | Brainstorm | `SET_AI_ACTIONS_PROMPT` | `brainstorm-ideas-with-me` | `aiActionWriteGroup` | [prompt-actions.md](prompt-actions.md) |
| Write | Write a script | same | `write-script` | `aiActionWriteGroup` | [prompt-actions.md](prompt-actions.md) |
| Write | Write an outline | same | `outlining-a-script` | `aiActionWriteGroup` | [prompt-actions.md](prompt-actions.md) |
| Write | Rewrite | same | `improve-and-rewrite` | `aiActionWriteGroup` | [prompt-actions.md](prompt-actions.md) |
| Sound good | Edit for clarity | same | `edit-for-clarity` (agent-routed) | `aiActionEditForClarity` | [prompt-actions.md](prompt-actions.md#non-text-actions-in-the-same-panel) |
| Sound good | Studio Sound | `INSERT_AI_EFFECT_FROM_CONDUCTOR` | effect | `aiEffectStudioSound` | [../../pseudocode/studio-sound.md](../../pseudocode/studio-sound.md) |
| Sound good | Remove filler words | `INITIATE_PROJECT_SEARCH` (filler search) | search results view | `fillerWordRemoval` | [../../pseudocode/filler-removal.md](../../pseudocode/filler-removal.md) |
| Sound good / Look good | Smooth jump cuts | `SET_AI_ACTIONS_PROMPT` | `smooth-jump-cuts` | `aiSpeechImputation` | [smooth-jump-cuts.md](smooth-jump-cuts.md) |
| Sound good | Generate audio | same | `generate-music` (music/SFX) | `soundGeneration` | n/a |
| Sound good | Remove retakes | same | `remove-retakes` (agent-routed) | `aiActionRemoveRetakes` | [../../pseudocode/retake-removal.md](../../pseudocode/retake-removal.md) |
| Sound good | Format transcript | `FIX_TRANSCRIPT {projectId}` | none | `aiActionFixTranscript` | n/a |
| Sound good | Shorten word gaps | `INITIATE_PROJECT_SEARCH` (gap search) | search results view | `shortenWordGaps` | [../../pseudocode/filler-removal.md](../../pseudocode/filler-removal.md) |
| Sound good | Add chapters | `SET_AI_ACTIONS_PROMPT` | `add-chapters` | `aiActionAddChapters` | [prompt-actions.md](prompt-actions.md) |
| Look good | Generative fill | `ENTER_CANVAS_OUTPAINT_MODE` | canvas mode | per media type | [../object-removal.md](../object-removal.md) |
| Look good | Quick design | `START_QUICK_DESIGN` | none ("Design your video": scenes, layouts, B-roll) | `aiActionWindowDressing` | gap |
| Look good | Eye Contact | `INSERT_AI_EFFECT_FROM_CONDUCTOR` | effect | `aiEffectEyeContact` | [../eye-contact.md](../eye-contact.md), [../../pseudocode/eye-contact.md](../../pseudocode/eye-contact.md) |
| Look good | Center active speaker (v1, v2) | `SET_AI_ACTIONS_PROMPT` | `center-active-speaker`, `center-active-speaker-v2` | `aiEffectCenterActiveSpeaker` | [../../pseudocode/center-active-speaker.md](../../pseudocode/center-active-speaker.md) |
| Look good | Green screen | `INSERT_AI_EFFECT_FROM_CONDUCTOR` | effect | `aiEffectGreenScreen` | [../../pseudocode/green-screen.md](../../pseudocode/green-screen.md) |
| Look good | Skin smoothing | same | effect | `aiEffectBeautify` | [../skin-smoothing.md](../skin-smoothing.md), [../../pseudocode/skin-smoothing.md](../../pseudocode/skin-smoothing.md) |
| Look good | Blur speaker background | same | effect | `aiEffectGreenScreen` | [../../pseudocode/blur-speaker-background.md](../../pseudocode/blur-speaker-background.md) |
| Look good | Automatic multicam | `SET_AI_ACTIONS_PROMPT` | `automatic-multicam` (needs video) | `aiEffectAutomaticMulticam` | [automatic-multicam.md](automatic-multicam.md) |
| Look good | Generate media | same | `generate-image` | image generation | [../../pseudocode/editor/stock-asset-providers.md](../../pseudocode/editor/stock-asset-providers.md#ai-image-generation-decompiled-no-generation-ran-in-the-capture) |
| Look good | Smart zoom | `SET_AI_ACTIONS_PROMPT`, then `APPLY_ANIMATIONS_PER_VALID_CARD_LAYER` | `smart-zooms` | `smartAnimations` | gap (flag `smart-pans-and-zooms` off for Hunter) |
| Repurpose | Create clips | `SET_AI_ACTIONS_PROMPT` | `make-clips` (agent-routed) | `aiActionRepurposeMediaGroup` | [prompt-actions.md](prompt-actions.md#non-text-actions-in-the-same-panel), [../../pseudocode/underlord/create-clips-workflow.md](../../pseudocode/underlord/create-clips-workflow.md) |
| Repurpose | Create highlight reel | same | `make-highlight-reel` | `aiActionRepurposeMediaGroup` | [prompt-actions.md](prompt-actions.md#non-text-actions-in-the-same-panel) |
| Repurpose | Find highlights | same | `find-highlights` | `aiActionRepurposeMediaGroup` | [../../../HANDOFF.md](../../../HANDOFF.md) backlog |
| Repurpose | Translate | same | `translate` | `aiActionTranslateCaptions` | n/a |
| Publish | YouTube description | same | `youtube-description-v2` | `aiActionPublishGroup` | [prompt-actions.md](prompt-actions.md), [../youtube-publish-ai.md](../youtube-publish-ai.md) |
| Publish | YouTube thumbnail | same | `youtube-thumbnail` (default style "clean-minimal") | `imageGeneration` | [../youtube-publish-ai.md](../youtube-publish-ai.md) |
| Publish | Show notes / Draft a title / Summarize / Social posts / Blog post | same | `show-notes-v2` / `suggest-title` / `summarize-v2` / `social-posts` / `blog-post` | `aiActionPublishGroup` | [prompt-actions.md](prompt-actions.md), [../../pseudocode/youtube-titles-descriptions.md](../../pseudocode/youtube-titles-descriptions.md) |
| AI Labs | Segment with text | same | `segment-with-text` | none | n/a |

"Agent-routed" presets (`edit-for-clarity`, `make-clips`, `remove-retakes`) are the ones the client marks as runnable through Underlord instead of the legacy action endpoint (decompiled preset sets in chunk 5433). The related docs [../enhance-video-suite.md](../enhance-video-suite.md) and [../video-regenerate.md](../video-regenerate.md) cover the Look good effects pipeline and the AI-speech regenerate that Smooth jump cuts uses.

Not observed in Hunter's capture: none of the prompt-action endpoints (`/open_ai/chat_completion`, `/projects/{id}/ai_actions/*`, `/media_generation/queue`) were called. Only `GET /projects/{id}/media_generation/jobs/active` (9 polls) appears.
