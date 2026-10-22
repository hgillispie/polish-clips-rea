# Animated story (pseudocode)

Spec: [../features/animated-story/README.md](../features/animated-story/README.md). Voice: [editor/voiceover.md](editor/voiceover.md), [voice-consent.md](voice-consent.md). Captions: [captions.md](captions.md). All of this is **design**.

```text
function animated_story(brief) -> Story:
  est = estimate_cost(brief); require_confirmation_if(est.cents > brief.budget_cents)
  script = write_script(brief)                               # user may edit; re-entry point
  cast, style = build_cast_and_style(script, brief)          # user approves sheets; re-entry point
  shots = storyboard(script, cast, style, brief)
  for s in shots (parallel, max 4 in flight):
    s.image = gen_consistent_image(s, cast, style)
  voice_lines(shots, cast, brief)                            # TTS with timestamps
  time_shots(shots, brief.target_s)
  for s in shots where motion_for(s, brief.animate) == "video": s.video = animate(s)
  for s in shots where s.motion != "video": s.motion = depth_ok(s.image) ? "parallax" : "kenburns"
  caps = captions_from_tts(shots)
  return assemble_story(shots, caps, brief)
```

## Script

```text
schema Screenplay = {title, logline, cast: [{name, role, description}], scenes: [{id, setting, shots: [
  {id, speaker: "narrator"|cast_name|null, line: string|null, emotion, action, shot_type: "wide"|"medium"|"close",
   camera: "static"|"push_in"|"pan_left"|"pan_right"|"tilt_up"|"orbit", est_s}]}]}

function write_script(b):
  facts = b.source_ref ? fact_sheet(b.source_ref) : null          # publish-metadata.md
  words = round(b.target_s * 2.6)
  return llm_json("story_script.v1", {idea: b.idea, facts, words, audience: b.audience, aspect: b.aspect,
                  beats: ["hook<=5s", "setup", "conflict", "resolution", "end_line"]}, schema=Screenplay, temperature=0.8)
```

## Cast and style

```text
function build_cast_and_style(script, b):
  style = b.style_ref_image ? {frame: b.style_ref_image, tokens: describe_style(b.style_ref_image)}
                            : {frame: gen_image(style_prompt(b.style_preset)), tokens: preset_tokens(b.style_preset)}
  style.palette = dominant_colors(style.frame, k=6)
  cast = []
  for c in script.cast:
    bible = llm_json("character_bible.v1", {c, style: style.tokens}, schema=Bible)   # palette hex, silhouette, 3 features
    sheet = c.user_ref ? [c.user_ref] :
            gen_image(sheet_prompt(bible, views=["front", "three_quarter", "side"], expressions=["neutral", "happy"]),
                      refs=[style.frame], size="1536x1024")
    cast.append(Character(name=c.name, bible, sheet_asset_ids=[sheet], voice_id=pick_voice(c, b.voices), ref_strength=0.8))
  settings = {sc.setting: gen_image(setting_prompt(sc.setting, style), refs=[style.frame]) for sc in script.scenes}
  return cast, style ∪ {settings}
```

## Consistent shot images

```text
function shot_prompt(s, cast, style):
  chars = characters_in(s.action, s.speaker, cast)
  return join([style.tokens, "Setting: " + s.setting,
               for ch in chars: ch.name + ": " + ch.bible.description + " (" + pose_expr(s, ch) + ")",
               "Action: " + s.action, "Shot: " + s.shot_type + ", camera " + s.camera,
               "No text, no watermark, no extra limbs, consistent proportions"])

function gen_consistent_image(s, cast, style, tries=3):
  refs = [style.frame, style.settings[s.setting]] + [ch.sheet_asset_ids[0] for ch in characters_in(s, cast)]
  seed = hash(s.id)
  for k in 0..tries-1:
    img = route("image.ref_conditioned", prompt=shot_prompt(s, cast, style), refs=refs, seed=seed + k,
                aspect=brief.aspect, ref_weight=min(1.0, 0.8 + 0.1*k))
    c = consistency(img, s, cast, style)
    if c.ok: return {asset: img, consistency: c, seed: seed + k}
  flag(s, "consistency"); return {asset: img, consistency: c, seed: seed + tries - 1}

function consistency(img, s, cast, style):
  sims = [max(dino_sim(crop, ch.sheet)) for ch, crop in detect_characters(img, characters_in(s, cast))]
  pal = palette_distance(img, style.palette)
  vlm = vlm_json("same_character_check.v1", {img, refs: sheets}, schema={same: bool, artifacts: bool, text_in_image: bool})
  ok = all(x >= 0.55 for x in sims) and pal <= 0.25 and vlm.same and not vlm.artifacts and not vlm.text_in_image
  return {ok, sims, pal, vlm}
```

## Voice, timing, motion

```text
function voice_lines(shots, cast, b):
  for s in shots where s.line:
    v = s.line.speaker == "narrator" ? b.voices.narrator : cast[s.line.speaker].voice_id
    require_consent_if_clone(v)                                   # voice-consent.md
    a = route("tts.timestamps", text=s.line.text, voice=v, style=s.line.emotion)
    s.audio = {asset_id: a.audio, words: a.words}                 # [{w, t0, t1}]

function time_shots(shots, target_s):
  for s in shots: s.dur = s.audio ? s.audio.len + gap(s) : max(1.5, s.est_s)    # gap 0.2–0.5 s; 0.8 at scene end
  total = Σ s.dur
  if abs(total - target_s) / target_s > 0.15: raise NeedsScriptAdjust(total)  # UI: trim/add lines via LLM

function animate(s):
  v = route("video.i2v", first_frame=s.image.asset, prompt=s.action + "; camera " + s.camera,
            duration=clamp(ceil(s.dur), 4, 8), aspect=brief.aspect, audio=false)
  if not frame_consistent(v, s.image.asset, cast): v = null; s.motion = "kenburns"; return null
  return fit_length(v, s.dur, max_stretch=0.15)                   # trim, or interpolate, or hold last frame

function motion_for(s, animate):
  return animate == "all" ? "video" : animate == "key" and s.is_key ? "video" : "still"
  # is_key: first shot, climax shot, and shots whose action has a verb of motion (LLM tag)
```

## Captions and assemble

```text
function captions_from_tts(shots):
  t = 0; cues = []
  for s in shots:
    if s.audio: for w in s.audio.words: cues.append_word(w.w, t + w.t0, t + w.t1)
    t += s.dur
  return group_cues(cues, max_words=3 if vertical else 7)        # captions.md grouping rules

function assemble_story(shots, caps, b):
  commit("Create animated story"):
    comp = create_composition(aspect=b.aspect)
    t = 0
    for s in shots:
      if s.video: add_video_layer(comp, s.video, t, s.dur)
      elif s.motion == "parallax": add_parallax(comp, s.image.asset, depth(s.image.asset), cam=s.camera, t, s.dur)
      else: add_image_layer(comp, s.image.asset, kenburns_from_camera(s.camera), t, s.dur)
      if s.audio: add_audio(comp, s.audio.asset_id, t)
      t += s.dur
    add_captions(comp, caps); if b.music: add_music(comp, pick_music(b), duck=-12)
  return Story(...)
```

## Errors

| Case | Behaviour |
| --- | --- |
| Image model refusal | Simplify the prompt (drop adjectives, keep refs) once. Then the shot becomes `failed` and the others continue |
| Video model timeout | Fall back to parallax. Mark it `fallback` |
| TTS failure | Retry with another voice of the same gender/age bucket only if the user allows it. Else `failed` |
| Budget reached mid-render | Stop new video jobs. Remaining key shots use parallax. Report this |
