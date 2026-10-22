# Underlord skill library

All entries are **decompiled** from the client skill registry in chunk 88 (one array of 21 records), unless a row says otherwise. Every body was read; this page paraphrases purpose and structure. No skill body text is reproduced. The raw extraction (ids, descriptions, gates, bodies, ref lists) is kept outside git on the research box under `decompile/recovered/underlord/`.

## Record shape

```text
Skill
  id            string        kebab id, unique; also the load_skill argument
  name          string        display name
  description   string        one paragraph: what it does + "invoke/load when ..."
  body          string        markdown playbook (some are built from a template function)
  isInvokable   boolean       may the user pick it (skills picker / slash token)?
  isViewable    boolean       may the user read the body in the UI?
  gate          Gate | Gate[] optional; every gate must match the session flags
Gate
  flag          string        remote feature flag name
  when          value | value[]   allowed flag values (true, "experiment-treatment", ...)
```

Three visibility classes fall out of the two booleans (**decompiled**):

| isInvokable | isViewable | Class | How the body reaches the model |
| --- | --- | --- | --- |
| true | true | **User workflow skill.** Listed to the user, body viewable | Returned as-is |
| true | false | **Confidential user skill.** Listed and invokable, body hidden | Wrapped with a marker tag and a trailing instruction not to disclose the body |
| false | false | **Agent guidance.** Never shown as a user skill | Wrapped as hidden guidance, with an instruction not to name or reveal it and to deny it exists as a skill if asked |

## Catalog (21 skills)

Gates: **MPS** = `agent-first-party-macro-skills` is `true`. **PS** = both `use-agent-skills-ux` and `use-personal-skills` are `true`. One flag-normalization helper in the client sets MPS to `true` whenever `use-agent-skills-ux` is `true`, and the UI-side check for macro skills requires `use-agent-skills-ux`, `use-personal-skills` and MPS together (**decompiled**; where that helper runs is not traced). "Experiment" = the flag value must be `experiment-treatment`.

| # | id | Name | Class | Gate | Body |
| --- | --- | --- | --- | --- | --- |
| 1 | `track-properties-reference` | Track properties reference | guidance | none | present (~10.9 KB) |
| 2 | `zoom-at-jump-cuts` | Zoom at jump cuts | guidance | none | present |
| 3 | `avatar-workflows` | Avatar workflows | guidance | none | present |
| 4 | `media-generation` | Media generation | guidance | none | present |
| 5 | `yt-thumbnail` | YouTube thumbnail | guidance | none | present |
| 6 | `video-planning-brief` | Video planning brief | guidance | none | generated at load time from the planning-prompt builder |
| 7 | `video-planning-questions` | Video planning questions | guidance | Experiment `exp-video-planning-questions` | present |
| 8 | `defensible-design-decisions` | Defensible design decisions | guidance | Experiment `exp-agent-design-layout-skills` | present (~6.5 KB) |
| 9 | `layout-design-references` | Layout design references | guidance | Experiment `exp-agent-design-layout-skills` | present (~16 KB) |
| 10 | `create-skill` | Create skill | confidential user skill | PS | present |
| 11 | `center-active-speaker` | Center active speaker | confidential user skill | `vs-cas-v2` is `true` | present (~6.1 KB) |
| 12 | `create-media-montage` | Create media montage | user workflow | MPS | present |
| 13 | `create-clips` | Create clips | user workflow | MPS | present |
| 14 | `edit-talking-head-video` | Edit talking-head video | user workflow | MPS | present |
| 15 | `edit-podcast-recording` | Edit podcast recording | user workflow | MPS | present |
| 16 | `translate-and-dub` | Translate and dub | user workflow | MPS | present |
| 17 | `generate-video-with-voiceover` | Generate video with voiceover | user workflow | MPS | present |
| 18 | `generate-an-animated-story` | Generate an animated story | user workflow | MPS | present |
| 19 | `turn-slides-into-video` | Turn slides into video | user workflow | MPS | present |
| 20 | `prepare-for-publish` | Prepare for publish | user workflow | MPS | present |
| 21 | `ask-underlord-for-suggestions` | Ask Underlord for suggestions | user workflow | MPS | present |

Personal skills (scope `user`) come from the backend at `/agent-instructions` and are appended to the catalog after the first-party ones (**decompiled**). Drive-scoped records exist in that API (`source: "drive"` is a legal `load_skill` value) but the catalog builder only appends `user` scope (**decompiled**); whether drive skills ever reach the catalog is a gap.

## The common macro-skill template

Every MPS workflow skill (rows 12–21) follows one layout. This is the part worth copying into our own design (**decompiled**, paraphrased):

1. **SET-UP.** A short list of questions, asked one at a time, briefly, waiting for each answer. Skip anything the user's message or the project already answers. Usually: get the source media uploaded if missing, then two to four choices (platform, aspect ratio, count, brand on/off, narration source...).
2. **Gate on media.** "Once the file is uploaded, proceed."
3. **WORKFLOW.** An ordered list of steps. Each step names an outcome and, where a specialist playbook exists, a `{{sub-skill-id}}` reference. Some steps are plain instructions (transcribe, make one composition per clip).
4. **INTERACTION.** Run in phases and pause at phase boundaries (after structure, before styling, before audio). Show what changed and confirm before moving on. Do not run start to finish unless told to.
5. **Follow-ups.** After finishing, offer two or three next actions. Cross-links to other macro skills use a `{{→ Display Name}}` form.

Two skills deviate on purpose: `translate-and-dub` says to start translating right after set-up with no plan approval, and `turn-slides-into-video` has a single set-up step and no phase pauses.

## Per-skill outlines (paraphrased)

### User workflow skills (MPS)

**`create-clips`.** Turns a long recording (podcast, interview, webinar, talk, livestream) into short social clips or audiograms.
- Set-up: source media; assume video clips unless the source is audio-only (then offer audiograms); target platform(s) and aspect ratio (16:9, 9:16 or 1:1); how many clips and any must-include moments; brand on or off.
- Workflow: transcribe if needed → find the strongest moments `{{find-highlights}}` → apply platform conventions `{{social-platform-style-reference}}` → one new composition per clip in the chosen ratio. Per clip: keep the speaker framed `{{center-active-speaker}}`, add captions `{{captions-and-kinetic-typography}}`, tighten and drop retakes `{{strategic-zooms-and-cuts}}`, brand if asked `{{apply-brand-kit}}`.
- Audiogram variant: waveform plus captions, no camera, and a generated illustration for two or three key moments per clip.
- Phased, then offer more clips, other ratios, or a publish package.

**`edit-talking-head-video`.** Single-speaker recording to a finished edit.
- Set-up: the recording; optional b-roll, images or music.
- Workflow: transcribe (not the b-roll) and label speakers → clean the script `{{remove-retakes-and-filler}}` → scenes and layouts `{{choose-layouts}}` → lower-thirds `{{add-speaker-lower-thirds}}` → tighten `{{strategic-zooms-and-cuts}}` → polish `{{polish-pass}}` → fill placeholders `{{fill-broll}}` → music if supplied or asked `{{background-music}}`.
- Phased; follow-ups to Create clips or Prepare for publish.

**`edit-podcast-recording`.** Audio or multicam podcast to a finished episode.
- Set-up: the main recording(s); if several camera or mic files, offer to stitch them into an aligned sequence; optional intro, outro, music.
- Workflow: transcribe the episode only, label speakers → clean the script and trim pre-show chatter → scenes and layouts → keep the active speaker on screen → lower-thirds → polish → intro, outro, music.
- Phased; follow-ups to clips or audiograms, or a publish package with show notes.

**`create-media-montage`.** Photos and clips into a montage (tribute, real-estate walkthrough, highlight reel).
- Set-up: montage type (drives order); use media already in the project or ask for uploads; original audio vs music; essentials (occasion, or address, specs, contact).
- Workflow: one scriptless scene per file `{{broll-montage-scenes}}` → layouts `{{choose-layouts}}` → order by type (a tribute opens on a title card and groups by theme with no outro; a property tour goes exterior, then rooms in walking order, then outdoor features, then back outside, with labels and contact details at both ends) → pace to the original audio or to a mood-matched track `{{background-music}}` → brand for business montages `{{apply-brand-kit}}`, clean styling for personal ones.

**`translate-and-dub`.** Captions or subtitles in other languages, optionally dubbed.
- Set-up: dub audio or just captions (default captions); find the video; target languages; burned-in captions or an `.srt` file.
- Then start immediately, with no plan approval.
- Workflow: wait for the transcript → per language: new composition, translate speech and captions, burn captions if wanted `{{captions-and-kinetic-typography}}` (translate existing captions rather than removing them), title the composition by language. Dubbing: pick native voices per speaker matching gender and tone `{{choose-voice}}`, neutral voices for unknown speakers, report the picks, and fall back to captions-only where a language cannot be dubbed.
- Finish with a language summary, export steps looked up in help (not guessed), and follow-ups.

**`generate-video-with-voiceover`.** Narrated video from a recording, a pasted script, or a topic.
- Set-up: video type (explainer, promo, profile, intro), which sets structure `{{script-narratives}}`, platform and length; narration source; avatar or not; brand or not.
- Workflow: narration (transcribe the recording / paste the script verbatim / write one from the topic) → AI voice if needed `{{choose-voice}}` → avatar `{{avatar-workflows}}` → scenes and layouts → fill placeholders → brand.
- Follow-ups: translate, clips, publish package.

**`generate-an-animated-story`.** Multi-scene AI-generated story (trailer style or illustrated children's story).
- Set-up: reuse anything in the project; subject, vibe, length; voiceover or visuals only; visual style.
- Workflow, with approval stops after each heavy step: one style-setting image `{{media-generation}}` refined until approved → propose cast and locations → plan scenes (narration via `{{script-narratives}}` or a visual beat sheet), sized to the generated clip length → character cards, approved → first frames per scene, approved → generate each scene's video → voiceover `{{choose-voice}}` → scene length follows clip length (split or generate more, never loop footage) → offer music and captions.

**`turn-slides-into-video`.** PDF deck to narrated video.
- One cohesive narration written across the whole deck, then chunked per slide; one scene per slide with the slide as the main visual; background color matched to the deck; no text overlays on slides; AI voice `{{choose-voice}}`.
- Afterwards offer a circular avatar presenter in a corner `{{avatar-workflows}}`, added only on confirmation.

**`prepare-for-publish`.** Publish package for a finished edit, text and images only. Never exports, renders, publishes or edits.
- Set-up: destination platforms and audience; optional tone or examples.
- Workflow: several titles → YouTube description with chapters (long videos get extra timestamp and hashtag guidance) → per-platform social posts `{{social-platform-style-reference}}` → YouTube thumbnail when YouTube is a target `{{yt-thumbnail}}`. Then offer iterations.
- Detailed spec in [../../pseudocode/youtube-titles-descriptions.md](../../pseudocode/youtube-titles-descriptions.md).

**`ask-underlord-for-suggestions`.** No set-up or phases. Inspect the composition, tracks and visuals first, then propose short, specific edits that the agent's own tools can carry out, that are not already done, that each point at a concrete target, and that recommend layouts only when there is a creative reason.

### Confidential user skills

**`center-active-speaker`** (gate `vs-cas-v2`). A static-crop reframing workflow driven by `query_face_tracking`:
1. Set the aspect ratio first; find the face-tracked video track.
2. Call face tracking. It may need to wait for server processing; stop and explain on no faces, an unsupported format, a length limit, or anything other than exactly one video source.
3. Read the returned plan: a whole-track baseline focal point plus speaker-aligned scene starts, each with an active face, a headroom-adjusted suggested focal point and median face boxes.
4. Apply in order: whole-track crop and scale first, then scene boundaries at each later start, then all per-scene focal points in one batched track edit. Re-runs replace earlier framing rather than stacking crops.
5. Verify with one screenshot of three or four scene midpoints. Fix only clear failures (wrong person, cut-off face, clipped head, canvas not filled).
Rules: never use screenshots to locate faces, never add the AI speaker-focus effect or keyframes, keep the previous crop where the active speaker is off camera.

**`create-skill`** (gate PS). Helps the user author a personal skill: settle the outcome in a beat or two (never field-by-field), write name, description and instructions itself, save with `save_skill` (create, published), never claim success on failure, and finish by emitting a skill token tag carrying the new id and name instead of dumping the content. Name rules: Unicode letters, numbers, spaces, `_ - .`, 1–100 characters after trimming.

### Agent guidance (hidden)

**`track-properties-reference`.** Reference for the 12 track types (script, audio, video, image, title, captions, shape, waveform, progress, placeholder, avatar) and which property groups apply to each: universal (name, gain, pan, mute, solo, timing), media descriptions, clip structure (media, gap, scratch, vector clips), audio effects (ducking, Studio Sound, reverb, compressor, EQ), fill behavior, text and styling, positioning in pixels or percent, layer state, caption word-state colors, and the GPU visual effects list. Explains that a "segment" is a track's intersection with a scene. Loaded before reading or writing track properties.

**`zoom-at-jump-cuts`.** Hide splices with a punch-in on the script layer: get legal times only from `query_jump_cuts`, split there, set content scale (default about 1.1–1.2×) and a speaker-centered focal point, skip very short beats, avoid pasting layout templates, vary framing rather than alternating mechanically. Explicitly not the AI "smooth jump cuts" heal and not a transition.

**`avatar-workflows`.** Avatar model and order of operations: avatars are 1:1 with speakers but have distinct ids; ungenerated → generated → stale lifecycle (most audio edits make it stale); where the reference image lives; create a custom avatar or pick stock, assign it, and generate last, with explicit user confirmation because generation is slow and blocks the editor; match voice gender.

**`media-generation`.** Rules for image and video generation prompts: describe scene content only, leave parameters (duration, ratio, model) out of the prompt, clamp unsupported values and say so, group multi-ratio results, and extend clips with remaining source footage (generative extension is a UI-only feature).

**`yt-thumbnail`.** Use the image tool's thumbnail template (the backend renders the title text), about four prompts for options, show the style presets and default to one if none is chosen, and include a real frame of the subject as a reference image.

**`video-planning-brief`.** The "creative brief" planning procedure, built at load time from the same function that otherwise injects planning into the system prompt. Enter planning for complex requests (from-scratch videos, multi-scene edits), ask questions only for real ambiguity, use query tools to validate values, present a `<creative-brief>` block plus a `<creative-brief-params>` block, wait for approval, then call `exit_planning` and only then edit. Simple one-shot requests (transcribe, remove filler, add captions, Studio Sound, change ratio...) must skip planning. Only a whitelist of read-only tools is allowed while planning.

**`video-planning-questions`** (experiment). When to ask instead of decide: default anything a query can answer or the plan can carry as a parameter, ask only when a wrong guess would destroy the user's own material or the request has two honest readings, ask once with two or three options and a recommendation alongside the plan, and never read the answer back.

**`defensible-design-decisions`** (experiment). Design taste for `design_scene_layout`: write a visual brief first, decide what the scene is for, design for motion over time rather than a still, and self-review for "generated taste".

**`layout-design-references`** (experiment). Reference values for typefaces and type sizes by role, contrast targets, talking-head and b-roll framing, motion timing ranges, one motion idea per scene, and a checklist of generated-looking patterns to avoid.

## How a skill gets used (summary)

Details in [observed-network.md](observed-network.md#skills-catalog-and-skills-observed-network):

1. At turn start the client filters the registry by the session's feature flags, adds the user's personal skills, and appends a catalog block to the system prompt. The block splits user skills (which may be named and listed) from agent guidance (never named).
2. The user can also pick a skill in the UI. That sends a user message whose content is a `<skill id="…">Name</skill>` token.
3. Either way the model calls `load_skill(id, source)`. Global skills are resolved in the client; user and drive skills are fetched from `/agent-instructions/{id}/content`.
4. The body comes back as a tool result, wrapped according to its visibility class. Nothing expands `{{refs}}`.
