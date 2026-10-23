# Publish and Write: the shared prompt-action pipeline

Descript's text-producing AI Tools (Publish and Write groups, plus Add chapters) all share one pipeline. Sources:

- **decompiled**: chunk 9105 for the action definitions, chunk 5433 for the preset enum and preset sets
- **static-bundle**: the endpoint paths
- **not observed**: none of these ran in Hunter's capture

Templates and prompt wording are not reproduced. The client builds a message from the parameters, and the server preset owns the actual prompt.

## Pipeline

```text
AI Tools item
  -> SET_AI_ACTIONS_PROMPT {presetId, entrypoint}         # opens the parameter panel in the sidebar
  -> user fills params, presses Run
  -> SEND_AI_ACTIONS_PROMPT.started {
        promptPresetId,                                   # e.g. "suggest-title"
        type,                                             # response renderer: None | Summarize v2 | ShowNotes v2 | Write
        version?,                                         # v2 presets
        message,                                          # client-built text: param labels + values + custom instructions
        analyticsCtx {..., initiated_by: "user"}
     }
  -> saga posts the legacy action endpoint:
        POST /open_ai/chat_completion?project_id=…&generation_trigger=…
        (the transcript / selection is attached server-side by project id; inferred)
  -> streamed or whole text lands in prompt.response
  -> responseComponent renders it (markdown text, list of titles, chapter list…)
  -> followupActions row under the result:
        [follow-up prompt button  (opens a free-text refine box, re-sends with the prior response as context),
         divider,
         Done                     (closes; for make-clips also opens the Project sidebar)]
```

Separate endpoints exist for non-text actions: `POST /projects/{id}/ai_actions/clips` and `POST /projects/{id}/ai_actions/scenes` (static-bundle).

Errors the client maps:

| Error | Shown as (paraphrased) |
| --- | --- |
| 400 `context_length_exceeded` | Script too long for this action |
| 400 content filter / safety | Request blocked |
| 402 | Paywall dialog for the action's `paywallId` |
| Clips action returned no clips | "No clips found" |

## Per action (inputs → output)

| Action | Preset id | Response type | Inputs (param keys; labels in parentheses) | Output | Paywall |
| --- | --- | --- | --- | --- | --- |
| Draft a title | `suggest-title` | None | `examples`, `customInstructions` | A list of title options | `publish_group` |
| Summarize | `summarize-v2` | Summarize v2 | `examples`, `customInstructions` | A summary paragraph or paragraphs | `publish_group` |
| Draft a blog post | `blog-post` | None | `examples`, `customInstructions` | Long-form markdown | `publish_group` |
| Draft a social post | `social-posts` | None | `style`, `amount` (number), `examples`, `customInstructions` | N posts in the chosen style | `publish_group` |
| YouTube description | `youtube-description-v2` | ShowNotes v2 | `examples`, `customInstructions` | Description with sections and timestamps | `publish_group` |
| Show notes | `show-notes-v2` | ShowNotes v2 | `examples`, `customInstructions` | Structured show notes | `publish_group` |
| Brainstorm | `brainstorm-ideas-with-me` | Write | `notes` (Starting point) | An idea list. Extra follow-ups for continuing the session | `write_group` |
| Write an outline | `outlining-a-script` | Write | `notes`, `audience`, `customInstructions` | An outline | `write_group` |
| Rewrite | `improve-and-rewrite` | Write | `style` (Editing style), `tone`, `audience`, `examples`, `customInstructions` | Rewritten script text | `write_group` |
| Write a script | `write-script` | Write | not located | A script | `write_group` |
| Add chapters | `add-chapters` | chapter list | `numberOfChapters` | Chapter markers with titles, applied to the composition | `add_chapters` |

Usage-feature ids from the paywall map (321839): `publish_group`, `write_group`, `edit_for_clarity`, `automatic_multicam`, `eye_contact`, `green_screen`, `center_active_speaker`, `studio_sound`, `regenerate_and_overdub`, `imputation_lip_sync`, `image_generation`, and others.

## Non-text actions in the same panel

| Action | What Run dispatches | Params | Paywall |
| --- | --- | --- | --- |
| Edit for clarity | its own started action | `editIntensity` Low / Moderate (2) / Heavy (4); `enableAISpeechOnSpeakers` ("Reword for flow"); `enableSmoothJumpCuts` ([smooth-jump-cuts.md](smooth-jump-cuts.md#edit-for-clarity-hook)) | `edit_for_clarity` |
| Create highlight reel | its own started action | `targetDuration` (Max duration), `templateDetails` (Layout) | `create_highlight_reel` |
| Remove retakes | its own started action | none | `remove_retakes` |
| Create clips, Find highlights | the legacy clips action, or Underlord | count, length, layout | repurpose group |

The **agent-routed** set (`edit-for-clarity`, `make-clips`, `remove-retakes`) can be handed to Underlord as a skill-driven turn instead of the legacy endpoint (decompiled preset set). Hunter's "make 3 short clips" went through the agent, not this panel ([../underlord/prompt-catalog.md](../underlord/prompt-catalog.md)).

## Full preset enum (decompiled, 5433)

add-chapters, animate-text, automatic-multicam, blog-post, brainstorm-ideas-with-me, center-active-speaker, center-active-speaker-v2, edit-for-clarity, edit-image-in-canvas, find-highlights, generate-image, generate-music, generate-sfx, generate-video, generate-visuals, improve-and-rewrite, make-clips, make-highlight-reel, outlining-a-script, remove-retakes-v2, segment-with-text, show-notes-v2, smart-zooms, smooth-jump-cuts, social-posts, suggest-title, summarize-v2, translate, window-dressing, write-script, youtube-description-v2, youtube-thumbnail.

The flag `gpt-prompt-presets` (seen in the flags response) carries remote overrides for these presets. Its values are not recorded here.

## For our build (inferred)

One `PromptAction {presetId, params schema, buildMessage(params, transcript), render}` table is enough. Point it at our own LLM call with our own prompts. Keep the follow-up prompt as "previous output + refine instruction".
