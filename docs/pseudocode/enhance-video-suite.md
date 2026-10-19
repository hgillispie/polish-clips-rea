# Enhance video suite

Orchestrator for Look Good effects that share one person matte, plus the local grades that do not. There is no `EnhanceVideo` symbol. Each effect is its own node. Analysis: [../descript-analysis/enhance-video-suite.md](../descript-analysis/enhance-video-suite.md). Types and the POST helper: [visual-effects-model.md](visual-effects-model.md).

Later than the polish-clip MVP. Not a pipeline stage.

## Who calls the mask

```text
MASK_TYPES = {
  "com.descript.backgroundBlur",
  "com.descript.backgroundRemoval",
  "com.descript.portraitLighting",
  "com.descript.uplighting"
}
```

That set is `background_mask.effectTypes` (**static-bundle**). One `POST /projects/{id}/background_removal` with `{asset_id}` fills `artifactType: "background_mask"` for every member.

```text
function sync_enhance_flags(media, effects) -> void:
  media.backgroundMaskRequested = any(effects, type in MASK_TYPES and enabled)
  media.portraitLightingRequested = any enabled com.descript.portraitLighting
  media.uplightingRequested = any enabled com.descript.uplighting
  media.eyeContactRequested = any enabled com.descript.eyeContact
  media.beautifyRequested = any enabled skin_smoothing
  media.speakerFocusRequested = any enabled com.descript.speakerFocus

function prepare_enhance(project_id, media, effects) -> Artifacts:
  sync_enhance_flags(media, effects)
  artifacts = media.artifacts or empty

  if media.backgroundMaskRequested or media.portraitLightingRequested or media.uplightingRequested:
    artifacts.background_mask = ensure_background_mask(project_id, media)   # green-screen.md
  if media.eyeContactRequested:
    artifacts.eye_contact = ensure_eye_contact(project_id, media)           # eye-contact.md
  if media.speakerFocusRequested:
    artifacts.face_tracking = ensure_face_tracking(project_id, media)       # center-active-speaker.md
  # beautifyRequested has no recovered POST. Skin runs locally and meters 5 credits on first file.
  return artifacts
```

`backgroundMaskRequested` is the mask flag. Portrait and uplight also set their own flags. The scheduler POSTs `background_removal` when any of the four types is on, even if only portrait is enabled (**inferred** join of `effectTypes` with the three flags). A second effect of the same four must not POST again while `artifacts.background_mask` is present.

## Apply order

```text
function render_enhance_frame(bitmap, effects, artifacts, t) -> bitmap:
  warn_if_portrait_and_uplight(effects)
  return apply_visual_effects(bitmap, effects, artifacts, t)
```

Recommended default order when the operator adds several at once (our order, index 0 first):

1. `com.descript.colorAdjustments`
2. `skin_smoothing`
3. `com.descript.backgroundRemoval` or `com.descript.chromakey` (not both; see below)
4. `com.descript.backgroundBlur`
5. `com.descript.portraitLighting` or `com.descript.uplighting`
6. `com.descript.eyeContact`
7. `com.descript.speakerFocus` last, because it reframes

The bundle does not record this sequence. It is the order that keeps a reframe from running before the matte exists. The operator can reorder. Render follows the array, not this recommendation.

## Portrait + Uplight

```text
function warn_if_portrait_and_uplight(effects) -> void:
  both = enabled portraitLighting and enabled uplighting
  if not both:
    return
  # Agent schema allows both (static-bundle). Help says the stack looks uneven (static-help).
  # No client reject was recovered (inferred from absence).
  require operator confirm "Portrait Lighting and Uplighting together look uneven. Apply both?"
  if declined:
    disable the one just added
```

Do not silently drop either node after the operator confirms.

## Green Screen vs chroma key

```text
function on_enable_green_screen(effects) -> void:
  if chroma key is enabled:
    warn "Chroma key is the local color key. Green Screen is the AI matte. Turn chroma key off?"
    # Agent copy prefers chromaKey for a solid-color backdrop (static-bundle).

function on_enable_chroma(effects) -> void:
  # chroma does not set backgroundMaskRequested and does not POST
  if green screen is enabled:
    warn "Green Screen already uses an AI mask. Chroma key ignores that mask."
```

Both can stay enabled if the operator insists. Apply order then keys twice. The warning is the spec, not a hard mutex.

## Per-effect specs

| Node type | File | Cloud |
| --- | --- | --- |
| `com.descript.portraitLighting` | [portrait-lighting.md](portrait-lighting.md) | shared mask |
| `com.descript.uplighting` | [uplighting.md](uplighting.md) | shared mask |
| `com.descript.backgroundBlur` | [blur-speaker-background.md](blur-speaker-background.md) | shared mask, 10 AI credits |
| `com.descript.backgroundRemoval` | [green-screen.md](green-screen.md) | owns the POST, 10 AI credits |
| `com.descript.chromakey` | [chroma-key.md](chroma-key.md) | none |
| `com.descript.colorAdjustments` | [color-adjustments.md](color-adjustments.md) | none |
| `com.descript.speakerFocus` | [center-active-speaker.md](center-active-speaker.md) | `face_tracking` |
| `com.descript.eyeContact` | [eye-contact.md](eye-contact.md) | `eye_gaze_correction`, 10 AI credits |
| `skin_smoothing` | [skin-smoothing.md](skin-smoothing.md) | no POST, 5 AI credits first file |

Self-record writes a local `background_mask` so the same shaders run without the POST: [editor/self-record-bg-remove.md](editor/self-record-bg-remove.md).

## Credits report

```text
EnhanceReport
  mask_task_id            string | null
  tracked_features        string[]     # aiEffectGreenScreen, aiEffectLighting, ...
  ai_effects_credits      integer | null
  warnings                string[]
```

Integers we will display as known: blur 10, green screen 10, eye contact 10, skin 5 on first file. Portrait and uplight display "AI credits" with no number. Center active speaker displays the category `ai_effects` with no number.

## Errors

| Case | Behaviour |
| --- | --- |
| Mask POST fails | Skip every MASK_TYPES node for this frame. Leave chroma, color, skin, and eye contact runnable |
| Eye-contact POST fails | Skip only `com.descript.eyeContact` |
| Face-tracking failureReason | Surface the mapped string from [center-active-speaker.md](center-active-speaker.md). Do not reframe |
| Operator cancels the portrait+uplight confirm | Disable the effect they just toggled |
| Missing speaker on a 10-credit effect | Do not POST. Point at the transcript speaker |

No Descript weights ship with this spec.
