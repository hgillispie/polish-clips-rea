# Underlord: what Hunter's signed-in capture shows

Written from one signed-in mitm capture that Hunter recorded on 2026-10-22, using web build `react19/a7c779e…`, app 153.0.4. The raw flows, the JS and the Wakaru output stay on the research box. This page records only field names, types, enums, tool names, step order, sizes and timings. It has no IDs, tokens, signed URLs, or prompt text.

Evidence tags: **observed-network** (in the capture), **decompiled** (Wakaru module from the signed build, call sites traced), **static-bundle** (a string in the signed JS, not traced), **inferred**.

This page supersedes the open questions in [agent-protocol.md](agent-protocol.md). Everything decompiled in that page held up, apart from the corrections noted below.

## Endpoints the agent touched (observed-network)

All calls go to `web.descript.com/v2/…`, with the same auth header as the rest of the editor.

| Call | Count | Notes |
| --- | --- | --- |
| `POST /agent/completions` | 80 | One call per model step. `call_source` is `main` (agent loop) or `screenshot_analysis` (vision sub-call made by the `screenshot` tool) |
| `GET /agent/chats` | 11 | Chat list for the project picker |
| `GET /agent_templates` | 12 | Public template gallery (32 items) |
| `GET /agent-instructions` | 6 | Published skills and instructions (9 items) |
| `POST /agent/search_help` | 2 | Backs the `search_help` tool. Body `{query}`; response `{result: string}`, a help-article context block. The source is Mintlify docs (**inferred** from the result layout) |
| `POST /projects/{id}/collab/commits` | many | How tool results reach the saved document (see below) |

The capture has no `/cloudagent/*` traffic, so this account runs the **local** (browser) loop. The flag `underlord-use-cloud-agent` resolved to `false`.

## Completion request (observed-network)

Top-level keys of the request body:

| Key | Type | Value pattern |
| --- | --- | --- |
| `project` | `{id, composition_id, commit_ref}` | `commit_ref` is the document revision the step was built on |
| `conversation_id`, `turn_id`, `request_id`, `assistant_message_id` | uuid strings | One turn = one user prompt. Each step gets a new `request_id` |
| `call_source` | `"main" \| "screenshot_analysis"` | |
| `agent_start_origin` | string | `"agent"` for typed prompts |
| `harness_id` | string | `mammoth-glm52-sonnet55-plain-text` |
| `model` | string | Main loop: `@preset/glm-5-2`. Screenshot sub-call: `anthropic/claude-sonnet-5.5` |
| `messages` | array | The whole history, resent on every step |
| `tools` | array, 72 entries | OpenAI `{type:"function", function:{name, description, parameters}}` |
| `stream` | bool | `true` for main, `false` for screenshot analysis |
| `persist` | bool | `true`. The server stores the conversation from the completion calls. No separate chat-save request was seen (**inferred**) |
| `context` | array | Screenshot sub-calls only |

No `tool_choice`, `temperature` or reasoning parameters are sent. The preset on the server side owns them (**inferred**).

### Message roles (observed-network)

| Role | Keys | Notes |
| --- | --- | --- |
| `system` | `content` (array of two text parts, both `cache_control: {type: "ephemeral"}`) | About 28k + 7.5k characters. The second part ends with the skills catalog (below) |
| `user` (`name: "user"`) | `id, name, content, context` | `content` is the typed text. `context` is the @-chips (below) |
| `user` (`name: "app-state"`) | `id, name, content` | A JSON string (later wrapped as one text part) with `currentTime` (ISO with offset), `compositionId`, `currentSceneId`, `sceneNumber`, `playheadTime`, `numScenes`, `numWordsInScript`, `viewportInfo`, `currentLayoutPackInfo`, `paywallStatus`, `isPlanning`. Sent right after every user prompt |
| `assistant` | `id, content, content_duration_ms, reasoning, reasoning_details, refusal, tool_calls` | `tool_calls[]` = `{id, type:"function", function:{name, arguments (JSON string)}, duration_ms}` |
| `tool` | `id, tool_call_id, name, status, content` | `name` is a **human label** ("Read script", "Found 16 matches", "Updated track"), not the tool name. `status` is `completed` or `failed`. `content` is a string, or `[{type:"text", text}]`, and starts with a `[ref:u2_X_Y]` handle that the model can cite back |

System-prompt section headings, as a list only: communication style, approach, billing (message costs, refunds), the Descript object model (composition, script and script–media alignment, tracks, placeholder and avatar pseudo-tracks, scenes, layers, transitions and animations, sequences, the target system), response strategy (search, efficient tool use, music and SFX, media display tags, target tags for links), planning, tone tags for AI speech, video editing guidelines, choosing a visual editing tool, authoring a layout into an occupied scene, available skills.

### Stream (observed-network)

`text/event-stream`, with lines `data: {chat.completion.chunk}`, ending in `data: [DONE]`.

- Chunk keys: `id, object, created, model, provider, choices[]`. The last chunk adds `service_tier` and `usage`.
- `choices[0].delta` keys seen: `role`, `content`, `reasoning`, `reasoning_details`, `tool_calls`.
- Tool-call deltas carry `index`, `id`, and `function.name` / `function.arguments` fragments.
- `finish_reason` is `tool_calls` or `stop`.
- `usage` has `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost`, `is_byok`, `prompt_tokens_details{cached_tokens, cache_write_tokens, audio_tokens, video_tokens}`, `completion_tokens_details{reasoning_tokens, image_tokens, audio_tokens}` and `cost_details{upstream_inference_cost, upstream_inference_prompt_cost, upstream_inference_completions_cost}`. This is the OpenRouter usage shape. `provider` names the upstream host (BaseTen for GLM).

Credits are not reported in the stream. They are a server-side conversion of `cost` (**inferred**).

### Screenshot sub-call (observed-network)

The `screenshot` tool renders frames in the browser and sends one non-streamed completion:

- `call_source: "screenshot_analysis"`, with no tools.
- One user message: two text parts (the intent and framing), then one or more `image_url` parts as `data:image/jpeg;base64` frames.

The reply is a short structured analysis: "matches intent: yes/no", what the frames show, and so on. The tool returns that analysis to the main loop as its result. The main model never sees the pixels.

## Client-side tool execution (observed-network + decompiled)

1. The stream ends with `finish_reason: tool_calls`.
2. The browser runs every call in that message, in parallel where the model batched them. For example, it ran three `copy_script_segments` calls in one step.
3. It appends one `tool` message per call and posts the next completion with the full history.
4. Document-changing tools produce collab commits: `POST /projects/{id}/collab/commits`.
   - Each commit is `{edit: {actionType, message}, graph: {delta}}`.
   - Agent edits are commits with `actionType` `AGENT/UPDATE_DOCUMENT_FROM_AGENT`, or a regular editor action such as `EDITOR/EFFECT/ENSURE_CARD_LAYER_COLOR_ADJUSTMENT`. Their message starts "Agent underlord: …" (for example "Updated 1 scenes", "result of request").
   - Delta sizes run from about 100 B to 50 KB.
5. Argument validation failures do not reach the server. The client returns a `failed` tool message ("Error parsing arguments for … Invalid tool call arguments"), and the model retries on the next step.

## "Auto" model selector (observed-network)

The model picker's **Auto** maps to the flag `default-v2-agent-harness`, which resolved to `mammoth-auto`. With `exp-agent-main-model-paid = glm52`, the request names harness `mammoth-glm52-sonnet55-plain-text` and model `@preset/glm-5-2`. "Sonnet55" in the harness id is the vision/screenshot model. "plain-text" is the tool-result format. The 112-harness table in [agent-protocol.md](agent-protocol.md) is otherwise right.

## @-context chips (observed-network)

Selecting script text with the agent panel open adds a chip to the prompt. It is sent as `user.context[]`:

```text
ContextItem
  type          "script-selection"         # only type seen
  id            uuid
  label         string                     # chip text, e.g. "before - on." = first word " - " last word of the selection (inferred rule)
  compositionId uuid
  sceneId       uuid
  scriptText    string                     # the selected text
  prefix        string                     # a few words before, for anchoring
  suffix        string                     # a few words after
```

Redux actions behind it (static-bundle, LLM/agent slice): `ADD_CONTEXT`, `REMOVE_CONTEXT`, `SYNC_SELECTION_CONTEXT`, `DISMISS_SELECTION_CONTEXT`, `CLEAR_CONTEXT`, `UPDATE_CONTEXT_UPLOAD_STATE`, `UPLOAD_FILES_TO_AGENT`, `UPLOAD_PDF_TO_AGENT`. The model resolved the chip by calling `find_in_script` with the chip's `scriptText`. See [../../pseudocode/transcript-model.md](../../pseudocode/transcript-model.md#selection-as-agent-context-descript-observed).

## Skills catalog and `/skills` (observed-network)

The system prompt ends with two blocks:

- `<user_skills>`: 11 entries, each **name** (id, source `global`) plus a one-line description.
  - `create-skill`, `create-media-montage`, `create-clips`, `edit-talking-head-video`, `edit-podcast-recording`, `translate-and-dub`, `generate-video-with-voiceover`, `generate-an-animated-story`, `turn-slides-into-video`, `prepare-for-publish`, `ask-underlord-for-suggestions`.
  - The model may name and list these to the user.
- `<agent_guidance>`: hidden playbooks that load the same way but are not to be offered as skills.
  - `track-properties-reference`, `zoom-at-jump-cuts`, `avatar-workflows`, `media-generation`, `yt-thumbnail`, `video-planning-brief`.

`load_skill` arguments are `{id, source, name}`. The bodies of `create-clips` and `ask-underlord-for-suggestions` came back as the tool result, with **no network request**, so those bodies ship in the client bundle. The picker and the opener are covered in [skill-picker-and-opener.md](skill-picker-and-opener.md).

## Templates, instructions, chats (observed-network)

```text
GET /agent_templates -> { data: AgentTemplate[], pagination: {} }
AgentTemplate
  id, slug, title, description, prompt, visibility ("public"), created_by, last_updated_by,
  created_at, updated_at, usage_count (int), share_link_url, meta_description,
  template_faqs (object[]), is_draft (bool), created_by_first_name, created_by_last_name,
  tags (string[]), is_descript (bool)
# 32 items, all public. Top tags: video, social, marketing, work, clips, highlights, podcast, shorts

GET /agent-instructions -> AgentInstruction[]
AgentInstruction
  id, type ("skill"), scope ("global"), name (slug-like), description, status ("published"),
  created_by, created_at, updated_at
# 9 items. Bodies come from GET /agent-instructions/{id}/content (static-bundle; not fetched in this capture)

GET /agent/chats -> { data: Chat[], pagination: {} }
Chat
  chat_id, project_id, title, harness_id, created_at, updated_at
```

The `agent-instructions` names overlap with the hidden guidance set (track properties, avatar workflows, media generation, video planning brief). They also include `create-skill`, `polish-pass`, `before-after-visual-comparison`, `consistent-character-generation`, and an internal test entry.

## Tool registry as sent (observed-network)

72 tools, against 86 names in the client registry. The flags for this account filter out the rest.

- **Script and transcript:** `query_script_markdown`, `find_in_script`, `edit_narration`, `correct_transcript`, `annotate_transcript`, `edit_inline_notes`, `shorten_word_gaps`, `assign_speaker`, `query_speakers`, `copy_script_segments`, `query_jump_cuts`.
- **Scenes and layout:** `query_scenes`, `add_scene_boundaries`, `modify_scene_boundaries`, `update_scene_properties`, `query_scene_layout`, `design_scene_layout`, `query_layouts`, `edit_chapter_markers`.
- **Tracks and compositions:** `query_tracks_v2`, `insert_track`, `modify_track`, `autosync_sequence`, `create_sequence`, `query_compositions`, `modify_composition_properties`, `modify_project`, `query_captions`.
- **Media:**
  - library and stock: `query_media_library_v2`, `search_stock_media`, `add_library_asset_to_project`, `import_external_media`, `search_drive`, `query_folders`, `manage_folders`, `inspect_media`, `wait_for_transcriptions`, `wait_for_visual_descriptions`, `screenshot`
  - brand: `copy_brand_asset_to_media_library`, `copy_brand_font_to_project`, `query_brand_kit`
- **Generation:** `generate_images`, `generate_video`, `generate_music`, `generate_sfx`, `generate_avatar_tool`, `create_custom_avatar`, `add_avatar_to_speaker_v2`, `query_stock_avatars`, `query_ai_voices`.
- **Effects:** `toggle-green-screen`, `toggle-background-blur`, `toggle-eye-contact`, `automatic_multicam`.
- **Translation:** `translate-composition`, `get_dub_speakers`, `update_translation_dub_and_speakers`.
- **Publish:** `export_video`, `publish_video`.
- **Help and web:** `search_help`, `web_search`.
- **Agent control:** `todo_write`, `enter_planning`, `exit_planning`, `load_skill`, `save_skill`, `delete_skill`, `compact_context`, `restore_context`, `summarize_context`, `undo_changes`.

Arguments and effects are in [agent-tools.md](agent-tools.md). Two of these tools are now documented from decompiled code: `query_jump_cuts` in [../ai-tools/smooth-jump-cuts.md](../ai-tools/smooth-jump-cuts.md#the-agents-jump-cut-tools-are-different) and `automatic_multicam` in [../ai-tools/automatic-multicam.md](../ai-tools/automatic-multicam.md).

## Approve, stop and undo (observed-network)

- **Plan approval.** No plan card appeared. `isPlanning` stayed false and `enter_planning` was never called, so the plan message format remains open.
- **Stop.** Hunter stopped the "pan to the guy in yellow" turn mid-loop. The client just stopped issuing completions; there is no cancel request in local mode.
- **Undo.**
  - Hunter then pressed undo in the editor. The capture shows five `EDITOR/DOCUMENT/UNDO` commits (message "undo"), one per agent commit. They are ordinary editor undo, not an agent call.
  - The `undo_changes` tool was offered to the model but never called. Its executor is gated by `exp-agent-undo-changes-tool` (decompiled).
  - No `rolledBackAt` / rollback request was seen.

## Flags that matter here (observed-network, flag response)

| Flag | Value |
| --- | --- |
| `underlord-use-cloud-agent` | false |
| `default-v2-agent-harness` | `mammoth-auto` |
| `exp-agent-main-model-paid` | `glm52` |
| `use-agent-skills-ux`, `use-personal-skills`, `agent-first-party-macro-skills` | true |
| `use-suggestion-empty-state` | true |
| `exp-auto-open-agent-sidebar`, `exp-agent-new-chat-on-load` | experiment-treatment |
| `ed-regenerate-ai-actions-integration`, `ai-actions-new-edit-review-state` | true |
| `magic-multicam` | true |
| `smart-pans-and-zooms`, `generate-visuals-action` | false |
| `agent-pricing-model` | `token-calculator-v1` |

## Find highlights / make clips (observed-network, backlog input)

- **Clip picking ran entirely in the model.** "make 3 short clips for tiktok" loaded `create-clips`, read the script once (`query_script_markdown`, 3 s timestamps), and then called `copy_script_segments` three times with time ranges.
  - There was no `find-highlights` request and no `/ai_actions/clips` call.
  - The AI Tools "Find highlights" and "Create clips" actions (presets `find-highlights`, `make-clips`) were not used in the capture.
  - Their client paths are in [../ai-tools/prompt-actions.md](../ai-tools/prompt-actions.md).
- **Highlight scoring was not observed.** No highlight endpoint fired, so there is nothing new about the server-side scoring.
