# Underlord agent tools

**decompiled** unless marked. Source: the tool-name enum (86 names, including 9 names used only as LLM "call sources" for sub-agents), the tool factory calls in the shared agent package (chunk 88), and the executor bindings in the app chunk. Descriptions below are our paraphrase of each tool's model-facing description and argument schema. Argument lists name the top-level fields; nested schemas are summarized.

## How a tool is defined

```text
Tool
  name             string           snake_case, must be in the call-source enum (the factory throws otherwise)
  parameters       zod object       sent to the model as JSON Schema (optionally $ref-deduplicated per model)
  description      string | fn      long model-facing usage guide; some are built per flag
  inProgressLabel  string           chat row text while running ("Reading script…")
  completedLabel   string           chat row text when done ("Read script")
  shouldEmit       boolean          default true; false hides the state-change event for that tool
  execute(ctx, args) -> ToolResult  optional; tools without one are returned to the caller unresolved
ToolResult
  content          string           text that becomes the tool message for the model
  updatedState     State?           new { doc, currentCompositionId, ... } if the tool edited the project
  images           [{url, detail, metadata}]?   attached as image parts (screenshots, renders)
  label            string?          overrides completedLabel
```

The executor gets the full turn context: API context, current state (the project document plus ids and the latest commit ref), the running message list, token usage, a `statusUpdate(text)` callback for live progress labels, and the call-source stack. Tools that need app services (media engine renders, uploads, redux selectors, backend calls) are declared in chunk 88 without `execute` and bound to an executor in the app chunk. We counted 52 such bindings.

Editor commands flagged `agent: true` in the editor command registry are wrapped into agent tools with their own labels. So part of the tool surface is literally the editor's command palette. The 20 commands we found: `translate-composition`, `set-edit-mode`, `export-video`, `open-help-resource`, the `add-*-layer` family (avatar, captions, dynamic text, placeholder, progress, shape, text, waveform), `toggle-background-blur`, `toggle-eye-contact`, `toggle-green-screen`, `toggle-studio-sound`, and `open-`, `delete-`, `create-` and `duplicate-composition`.

Tools are grouped by **drive-admin feature group** (`translation`, `ai_effects`, `script_editing`, `ai_media_generation`, `ai_speech`, or none). If an admin disables a group, those tools are removed from the list and the system prompt gets a short "disabled by your drive administrator" section naming the groups.

## Targets

A shared convention (system prompt section `tool_target_types`):

- **PositionTarget**: text anchor plus before/after (with prefix/suffix to disambiguate), a time offset in seconds, or end of composition.
- **RangeTarget**: time range, text range, one scene, several scenes, scene at time, scene at text, time inside a scene.
- **Track targets**: a track id, `"script"` for the main track, or `"currently_selected"` for the user's selection.
- Composition ids accept `"current"`. All times are decimal seconds. Targets are passed as JSON strings validated against the schemas inside each tool.
- Tool results carry a 5-character `[ref:xxxxx]` prefix so compaction tools can point at them.

## Registry

"Runs" = **inline** (executor in the shared agent package, pure function over the document), **app** (bound executor in the app chunk), or **unresolved** (declared without an executor and no binding found in the chunks we have; likely in a chunk we did not download, or server-side). "Group" = drive-admin feature group.

### Reading the project

| Tool | Args | What it does | Runs |
| --- | --- | --- | --- |
| `query_script_markdown` | composition_id, timestamp_frequency, include_highlights, filters{paragraph_indexes, sceneRange, timeRange, speakers} | Returns the transcript as annotated markdown: speaker tags, chapter markers, paragraph indexes, periodic timecodes, cut (`ignored`) text, AI-speech (`scratch`) text, scene markers, inline notes, optional highlight spans | inline |
| `find_in_script` | query (text, text-all, regex pattern, scene-boundaries, speaker-changes, silence-gaps, filler-words, highlights) | Searches the script and returns ready-made target strings for edit tools | inline |
| `lookup_timestamps` | (no schema in client) | Present only as a name in the enum and group map | ? |
| `query_compositions` | none | Lists compositions with id, name, duration, folder, video/audio, translation info | inline |
| `query_scenes` | composition, scene filter, properties | Scene timing, layout, transitions, backgrounds | app |
| `query_tracks_v2` | composition, range, tracks, properties | Track and layer properties per scene segment; see the `track-properties-reference` skill | inline |
| `query_layer_properties` | layerIds or use selection, properties | Property values of given layers | inline |
| `query_speakers` | compositionId, scope | Existing speakers and what each can do (voice, avatar) | unresolved |
| `query_face_tracking` | composition_id, start, end | Server face tracking turned into a scene-by-scene framing plan (baseline focal point, scene starts, active face, suggested focal point, face boxes) | app |
| `query_jump_cuts` | compositionId | Splice points on the talking-head track with exact composition times and eligibility | inline |
| `query_media_library_v2` | filters | Media-library files with metadata and visual descriptions | inline |
| `query_folders` / `manage_folders` | filters / create-folder or move operations | Read and reorganize project folders | inline |
| `query_layouts` | layoutPackId, maxResults, offset, filter | Layouts in a layout pack | app |
| `query_scene_layout` | sceneId, compositionId | A scene's composition as a flexbox-style layout tree (experiment) | unresolved |
| `query_captions` | none | Available caption styles; the model shows the 4 best matches | app |
| `query_kinetic_typography_presets` | none | Kinetic-typography presets and their visual descriptions | app |
| `query_brand_kit` | brandKitId, includeColors, includeMedia, includeFonts | Brand colors, gradients, assets, fonts | unresolved |
| `query_ai_voices` | language, search, age, gender | Stock and custom AI voices | app (group ai_speech) |
| `query_stock_avatars` | none | Stock avatars that can be assigned | unresolved (group ai_media_generation) |
| `get_dub_speakers` | language | Speakers and voice ids for dubbing a translation | app (group ai_speech) |
| `screenshot` | positions or range, max frames, detail | Renders canvas frames and returns them as images. A variant routes them through an image sub-model and returns text | app |
| `inspect_media` | items, intent | Renders library items (videos as sampled frames) to a multimodal sub-model and returns structured text | app |
| `wait_for_transcriptions` | composition_id | Blocks until pending transcription finishes or times out | app |
| `wait_for_visual_descriptions` | folder_name, media_ref_ids | Blocks until media visual descriptions are ready | app |
| `lint_project` | scope (new or all), screenshotsPerRule | Runs the visual/structural linter on demand | app |

### Editing the script and timeline

| Tool | Args | What it does | Runs |
| --- | --- | --- | --- |
| `edit_narration` | edits, composition_id, continuation_index | The main script editor. Two modes: **operations** (ignore, delete, replace, insert, rerecord at targets) and **tagged_script** (rewrite a chunk with inline `[[INSERT]]`, `[[REPLACE]]`, `[[RESTORE]]`-style markers, used for new scripts and long contextual rewrites, chunked for long media). Replace and insert of words create AI speech (scratch) and can trigger voice and video regeneration | inline (largest tool, ~39 KB) |
| `correct_transcript` | operations | Fixes transcript text without touching audio or video | inline |
| `annotate_transcript` | operations | Adds or removes bold, italic and colored highlight annotations on text ranges | inline |
| `copy_script_segments` | source{range, cut}, destination{composition or new name, position, range or append} | Copy, cut and paste script content within or across compositions; can create a new composition | inline |
| `shorten_word_gaps` | minGapDuration, targetGapDuration, compositionId | Shortens pauses above a threshold to a target length | inline (group script_editing) |
| `assign_speaker` | speaker, paragraphIndices | Sets or creates the speaker on paragraphs | app (group ai_speech) |
| `edit_inline_notes` | operations, compositionId | Inline notes, including voice-direction tags for AI speech | inline |
| `edit_chapter_markers` | operations, compositionId | Add, remove or edit chapter markers | inline |
| `add_scene_boundaries` | insertPositions, compositionId | Splits scenes at positions, including duration-based and empty scenes; returns new scene ids | inline |
| `modify_scene_boundaries` | operation (delete or move), compositionId | Deletes or moves scene boundaries | inline |
| `update_scene_properties` | compositionId, updateOperations (or sceneIds + properties in the older schema) | Per-scene layout id, background color or paint, transitions | app and inline (two definitions; which wins depends on the toolset) |
| `insert_track` | insertion{type: media-script, media-overlay-position, media-overlay-range, text-overlay, shape-overlay, placeholder, waveform, progress-indicator, captions}, compositionId | Adds media to the script track or as overlays, adds text, shapes, placeholders, waveforms, progress bars and captions | app |
| `modify_track` | track target, range or scenes, properties | Sets track or layer properties (crop scale and focal point, position, size, styling, effects, audio effects, fill behavior); the workhorse for framing | app |
| `apply_zoom_at_jumpcuts` | scale | Batch punch-in at every eligible jump cut | app |
| `automatic_multicam` | cameraAssignments, settings, videoSelectionRules | Builds speaker-driven camera switching scenes | app |
| `create_sequence` | mediaRefIds, displayName | Combines files into a multitrack sequence | inline |
| `autosync_sequence` | sequenceRefId | Aligns sequence tracks by audio | app |
| `create_kinetic_typography` | script range, text layer or image source, preset | Preset-based animated text from a script range; runs the kinetic-typography sub-agent stages | app |
| `design_scene_layout` | sceneId, compositionId, videoContext, sceneContent, designDirection, referenceMediaRefIds (or a raw layout tree + animations in the direct variant) | Delegates one scene's visual composition to a design sub-model (experiment) | app |
| `modify_composition_properties` | composition_id, properties | Rename, change orientation, convert between video and audio | inline |
| `modify_project` | operation (create, duplicate, open composition) | Composition lifecycle | app |
| `take_clip` | targetRange, compositionId, audioOnly | Renders a range to a short mp4 or audio clip in the browser media engine, saves it to the project and shows it in chat (flag `agent-take-clip-tool`) | app |

### Media, generation and brand

| Tool | Args | What it does | Runs |
| --- | --- | --- | --- |
| `search_stock_media` | query, stockMediaType (footage, music, sfx, backgrounds, photos, gifs, stickers), filters, intent | Stock search. One variant returns thumbnails; the other ranks candidates with an image sub-model and returns the picks as text | inline |
| `import_external_media` | source | Imports a URL or stock item into the media library | app |
| `add_library_asset_to_project` | assetId, libraryId, libraryType, mediaType, displayName | Brings a drive-library, other-project or brand asset in | app |
| `generate_images` | prompts (optionally a prompt template such as the thumbnail template, template params, reference image ids) | AI images, auto-imported as media refs | app (ai_media_generation) |
| `generate_video` | prompt, image(s), style, orientation, durationSeconds, generateAudio | AI video clip | app (ai_media_generation) |
| `generate_music` | prompt, durationSeconds, genre, mood, avoid, bpm, lyrics | AI music track | unresolved (ai_media_generation) |
| `generate_sfx` | prompt, durationSeconds, loop | AI sound effect | app (ai_media_generation) |
| `create_custom_avatar` | mediaRefId | Creates a backend avatar from an image | app |
| `add_avatar_to_speaker_v2` | speakerId, avatarId, compositionId | Assigns an avatar to a speaker | app |
| `generate_avatar_tool` | none | Starts avatar video generation; blocks editing until done | app |
| `update_translation_dub_and_speakers` | compositionId, speakers | Adds dubbing or changes speakers on a translation | app (ai_speech) |
| `translate-composition` (editor command) | compositionId, language, dubSpeech, includeLipSync, speakers | New or refreshed translation composition | app (translation) |
| `toggle-green-screen`, `toggle-background-blur`, `toggle-eye-contact` (editor commands) | enabled, amount or composition | AI visual effects | app (ai_effects) |
| `copy_brand_asset_to_media_library` / `copy_brand_font_to_project` | brandAssetGuid, displayName / fontAssetGuid | Brand kit to project | unresolved / app |

### Output

| Tool | Args | What it does | Runs |
| --- | --- | --- | --- |
| `export_video` | useCurrentComposition, compositionIds | Exports mp4 to the user's computer | app |
| `publish_video` | none | Opens the publish dialog for the user to confirm; the agent does not publish silently | app |

### Conversation management and meta

| Tool | Args | What it does | Runs |
| --- | --- | --- | --- |
| `enter_planning` / `exit_planning` | none | Enter or leave planning mode; edits are only allowed after leaving | app |
| `todo_write` | todos[{content, status: pending, in_progress or completed, activeForm}] | Visible task list | app |
| `compact_context` | summary, start, end | Shrinks the arguments and results of earlier tool calls in place (handled inside the loop) | inline (loop) |
| `restore_context` | ref | Returns the original text of a compacted tool call | inline (loop) |
| `summarize_context` | summary, end | Replaces earlier messages with the model's summary; only after a context-limit warning or on user request | inline (loop) |
| `edit_memory` | mode (append, replace, delete, clear_scope), scope, old_text, new_text | Edits the user's saved preferences ("Underlord Instructions") | app |
| `load_skill` | id, source (global, drive, user), name | Loads a skill body (see [observed-network.md](observed-network.md#skills-catalog-and-skills-observed-network)) | app |
| `save_skill` / `delete_skill` | mode, name, description, content, id, status / id, name | Personal skill CRUD via `/agent-instructions`; delete must be confirmed by the user in chat | app |
| `search_help` | query | Searches Descript help (Zendesk, or Mintlify behind a flag) via `/agent/search_help` | inline |
| `web_search` | query | Cited web answer; alternatively the gateway's native web-search plugin is attached (flag `agent-web-search-enabled`) | inline |
| `search_drive` | query | Searches the drive (exact args not resolved) | unresolved |
| `log_wishlist` | diagnosis, wishlist | Model reports tool friction to an analytics event; does not touch the project (flag `agent-wishlist-tool`) | inline |

### Sub-agent call sources (not tools)

These names appear in `call_source` on completion requests made by tools or hooks: `main`, `post-turn-verification`, `search_stock_media_analysis`, `screenshot_analysis`, `inspect_media_analysis`, `kinetic_typography_moment_selection`, `kinetic_typography_chunking`, `kinetic_typography_emphasis`, `kinetic_typography_placement`. Model slots for them: `main`, `scriptTool`, `sceneTool`, `multimodal` (falls back to `main`), plus `agent-design-models` for the design delegate.

## Toolsets per harness

| Toolset | Contents |
| --- | --- |
| Full | Base list (every tool above) plus `enter_planning` and `exit_planning` |
| Delegate-design | Full, minus the direct layout tool, with the delegating `design_scene_layout` |
| Experimental media gen | Full with alternate `generate_images` and `generate_video` |
| One-shot / no generation | Base list minus generation, avatar, dub-speaker, voice and speaker-assignment tools (used by public-API "one-shot" style harnesses) |

Per-turn filters then drop tools: `take_clip` unless its flag is on, GIF stickers unless the drive allows them, admin-disabled groups, and the compaction tools when the context policy says compaction is unavailable.
