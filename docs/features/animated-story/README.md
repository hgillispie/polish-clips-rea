# Generate an animated story

Turn a prompt, an outline or an existing transcript into a short animated video. The pipeline is:

**script → storyboard → per-scene image/video generation → TTS narration and character voices → captions → assembly**

The main requirement is that **characters and style stay consistent** across scenes.

Pseudocode: [../../pseudocode/animated-story.md](../../pseudocode/animated-story.md).

## Evidence

**Descript (decompiled).**
- `generate_images {prompts}`.
- `generate_video {prompt, image, style, orientation, durationSeconds, generateAudio}`: image-to-video, a style, an orientation and audio.
- The `generate-visuals` AI action preset, behind the `generate-visuals-action` flag, which was off.
- Stock providers ([stock-asset-providers](../../pseudocode/editor/stock-asset-providers.md)).
- AI voice and voiceover ([voiceover](../../pseudocode/editor/voiceover.md)).

Our tools take the same shape: per-call generation primitives the agent can chain. **No story pipeline was observed**, so everything below is **design**.

**Public research.**
- **Consistency methods:**
  - StoryDiffusion, consistent self-attention ([arXiv 2405.01434](https://arxiv.org/abs/2405.01434))
  - IP-Adapter, image prompts ([2308.06721](https://arxiv.org/abs/2308.06721))
- **Reference-conditioned image models:**
  - Gemini 2.5 Flash Image, "nano-banana", which takes multi-image references for character consistency ([docs](https://ai.google.dev/gemini-api/docs/image-generation))
- **Video models with first-frame and reference conditioning:**
  - Veo ([docs](https://ai.google.dev/gemini-api/docs/video))
  - Runway Gen-4 references
  - Kling
- **TTS with word timestamps:**
  - ElevenLabs ([with timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps))

## User stories

- "A 60-second story for kids about a fox who learns to share, watercolour style, 9:16." I get:
  - a script, which I can edit
  - 8 storyboard cards, each with an image, a line and a camera note
  - consistent Fox and Owl across every card
  - narration in a warm voice, with Owl in its own voice
  - captions
  - gentle motion on every scene
- **Cheap edits.** I change scene 4's line and only scene 4 re-renders. I swap the art style and keep the script, which re-renders the images but keeps the timing.
- **Explainer.** I paste my podcast transcript and choose "explainer, 90 s". It becomes a narrated animated summary that uses my cloned voice (with consent via [voice consent](../../pseudocode/voice-consent.md)).

## UX (design)

1. **Brief.**
   - Idea or source (prompt / outline / transcript / document).
   - Length (15–180 s), aspect, audience.
   - Style preset: watercolour, 3D clay, flat vector, anime, comic, photoreal (restricted for real people), or a custom reference image.
   - Narration voice(s); music on/off.
2. **Script.**
   - An editable screenplay: scenes with narration/dialogue, an on-screen action, and an estimated duration from words / 2.6 wps.
   - A duration meter against the target.
3. **Cast and style sheet.**
   - The app proposes characters with a description and generates a **character sheet** (front, ¾ and side views, 2 expressions) per character, plus a **style frame**.
   - I approve or regenerate them. I can upload my own reference image for a character.
   - This sheet is the consistency anchor.
4. **Storyboard.**
   - One card per shot: image, shot type (wide/medium/close), camera move, line, duration.
   - Regenerate, edit prompt, lock, reorder.
   - "Animate" per card (image→video) or "Still + Ken Burns" (cheaper).
   - The cost estimate updates live.
5. **Render.** Progress per scene. Failed scenes are flagged with retry, and the rest stay usable.
6. **Edit in timeline.** The result is a normal composition: scenes as layers, narration as an audio track with a transcript, captions. Everything stays editable.

## Inputs / outputs

```text
input: brief {idea | source_ref, target_s, aspect, audience, style_preset | style_ref_image, voices{}, music, animate: "all"|"key"|"none"}
output: Story { script, cast[], style_sheet, shots[], audio{narration, music}, captions, composition_id, cost }
```

## Algorithm (design)

1. **Script.**
   - An LLM writes a structured screenplay. Inputs: the target words (`target_s × 2.6`), the audience reading level, the beats (hook in the first 5 s, a setup, a conflict, a resolution, an end line) and the cast list.
   - For a source transcript: summarize first (fact sheet as in [publish metadata](../publish-metadata/README.md#algorithm-design)), then script from the facts only, so nothing is invented about real events.
   - Output scenes → shots, each with a line, a speaker, an action and a setting.
2. **Cast bible.**
   - Each character gets a canonical text description: species/age, silhouette, palette hex, clothing, and 3 distinctive features.
   - A **character sheet** image is generated once at high quality.
   - Settings get a reference image too.
   - A **style frame** fixes the palette, line weight and lighting.
3. **Shot prompts.** Template: `[style tokens] + [setting ref] + [character refs with pose/expression] + [action] + [shot type + camera] + [negative: text, watermark, extra limbs]`.
   - Character names never go to the image model alone. It always gets the bible description and the **reference images**.
4. **Image generation with consistency.**
   - The primary path is a reference-conditioned image model ("nano-banana"-class, multi-image input), given the character sheet(s), the style frame and the setting reference.
   - **Consistency check** per image:
     - a face/character embedding similarity to the sheet (CLIP/DINOv2 crop similarity ≥ threshold)
     - the palette distance to the style frame
     - a VLM yes/no on "Is this the same character as the reference? Any text or artifacts?"
   - Retry up to 2 times with a seed change and stronger reference weighting. Then flag the card for the user.
   - Fallbacks: IP-Adapter / StoryDiffusion-style pipelines on open models when self-hosting.
5. **Motion.**
   - Image→video for "key" shots: 4–8 s, first frame = the approved image, with the camera move from the storyboard.
   - A reference-to-video model when the character must move a lot.
   - The rest use Ken Burns or parallax (2.5D: depth map → layered pan) from the approved still. This is cheap and on-model.
   - Clip length is fitted to the narration: trim, or hold the last frame. Stretch at most 15% via frame interpolation.
6. **Voice.**
   - TTS per line with word timestamps. The narrator and each character get a voice.
   - Emotion tags come from the script.
   - Voice cloning is only with consent and only for the user's own voice.
   - Lines are joined with natural gaps (200–500 ms, longer at scene ends).
7. **Timing.** The narration drives the shot durations: `shot.dur = line audio + gap`, minimum 1.5 s. The visual-only beats use the storyboard estimate. The total is checked against the target, and the script trims or adds lines if it is off by more than 15%.
8. **Captions.**
   - From the TTS timestamps, which are exact, so no ASR is needed.
   - Styled per aspect, in the safe zone ([platform-profiles](../publish-metadata/platform-profiles.md#safe-zones-916-10801920)).
9. **Music and SFX** (optional). A library or generated track at a mood fit, ducked under the narration. Per-scene SFX from the script actions (generated SFX or a library).
10. **Assemble.** A composition with one layer per shot (video or still with keyframes), the narration track, captions, music and title/end cards. Packaging via publish metadata.

## Models / APIs (options)

| Step | Default | Options | Cost note |
| --- | --- | --- | --- |
| Script | mid-tier LLM, JSON | any | small |
| Character sheet / shots | Gemini 2.5 Flash Image ("nano-banana") | Imagen, FLUX Kontext, GPT-image; open: SDXL + IP-Adapter | per image; regenerations dominate |
| Image→video | Veo-class (first frame + prompt) | Kling, Runway Gen-4, Sora-class, Seedance | the most expensive step; default "key shots only" |
| Depth for parallax | Depth Anything v2 | MiDaS | local |
| Consistency check | DINOv2/CLIP crop similarity + VLM yes/no | — | cheap |
| TTS | ElevenLabs (timestamps) | Gemini TTS, OpenAI TTS, open: Kokoro/XTTS | per character |
| Music/SFX | library | generated music/SFX | — |

The model choice is a `ModelRouter` route, so vendors can be swapped. Every call is cached by `(model, prompt_hash, ref_hashes, seed)`.

## Data model

```text
Story { id, brief, script: {scenes: [{id, shots: [shot_id]}]}, cast: [Character], style_sheet: {frame_asset_id, tokens, palette[]},
        shots: [Shot], audio: {narration_track_id, music?}, captions_track_id, composition_id, cost_cents, status }
Character { id, name, bible: {description, palette[], features[]}, sheet_asset_ids[], voice_id, ref_strength }
Shot { id, scene_id, line?: {speaker_id, text, emotion}, action, setting_id, shot_type, camera, est_s,
       image: {asset_id, prompt_hash, seed, consistency: {sim, palette_dist, vlm_ok}}, motion: "video"|"kenburns"|"parallax",
       video_asset_id?, audio: {asset_id, words: [{w, t0, t1}]}, dur_s, locked, status }
```

## Edge cases

- **Real people or brands.** No photoreal likeness of real people without their consent. Logos only if provided by the user. A policy check runs on the script and the prompts.
- **Child-directed content.** Safe-content filters stay strict. No scary imagery for the "kids" audience.
- **Text in images.** Avoid it (models misspell). Put on-screen text as editable title layers instead.
- **The model refuses or drifts.** Retry with a simplified prompt. After the retries, keep the previous approved image and flag the shot.
- **Very long stories (> 3 min).** Chapter into acts and render incrementally. Cost confirmation per act.
- **Language.** The script and TTS share a language. Captions come from TTS timestamps in that language.

## Eval / metrics

- **Character consistency:** mean crop similarity to the sheet, and the human "same character?" rate ≥ 95% of shots.
- **Style consistency:** palette distance variance.
- **Narration-to-picture alignment:** a VLM check that the shot depicts the line's action.
- **Watch-through:** human rating of "would watch to the end".
- **Cost:** cents per finished minute (budget target set per plan).
- **Regenerations per shot:** target ≤ 1.3.

## MVP vs later

- **MVP:**
  - script → cast bible + sheets → storyboard stills (reference-conditioned) → Ken Burns/parallax motion
  - TTS narration with timestamps → captions → assemble
  - per-shot regenerate and lock; cost estimate
- **Later:**
  - image→video for key shots
  - multiple character voices with emotion
  - lip-sync for speaking characters
  - music/SFX generation
  - transcript-to-explainer mode
  - user-trained character LoRA
  - series memory (reuse a cast across episodes)
