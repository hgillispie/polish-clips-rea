# UI surface

Behavioural regions and the wires between them. Not a layout spec, and not the Descript window. Pixel positions, colors of the chrome, and control icons are free for the implementation as long as these wires hold.

## Regions

```text
Transcript panel
  Shows Transcript.words in order.
  Ignored words draw with a strikethrough and stay selectable.
  Filler and retake flags may show a marker; the flags are the data, the marker is optional.
  A selection is Selection (anchor word, focus word).

Timeline
  One row per Track, bottom track at the bottom of the stack.
  Clips as blocks from start_seconds to start_seconds + duration_seconds.
  Skip ranges, before they are ripple-closed, draw as gaps inside the block.
  Playhead is one composition time, shared with the preview.

Preview
  composite_frame(composition, playhead) at the composition size, scaled to fit the region.
  Plays audio from mix_interval for the block under the playhead.
  Caption glyphs paint here even when export burn-in is off.

Inspector
  Follows the current target: a clip, a caption style, or a word span.
  Caption target edits CaptionStyle fields from caption-style.md.
  Audio target edits AudioClipSettings (gain, fades, pan, mute, highpass, lowpass, studio_sound effect).
  Video target edits VisualLayer.transform, crop, and opacity.

Transport
  play, pause, seek(time), current time readout.
```

The polish pipeline does not draw these regions. When `open_in_editor` is set, the pipeline's `Composition` is what they bind to ([overview.md](overview.md)).

## Wires

```text
on transcript pointer down at word W:
  selection.anchor = W
on transcript pointer drag to word V:
  selection.focus = V
  range = selection_to_timeline(composition, selection)
  timeline.highlight = range
  inspector.target = clip of range

on transcript strike (keyboard or button) for the selection:
  ignore_words(composition, transcript, ids, reason="manual")
  # apply_ignores_to_timeline ripples linked clips and rebuilds cues
  preview.invalidate()

on transcript restore for the selection:
  clear ignored on those words
  apply_ignores_to_timeline again
  if a piece was rolled or slipped: confirm, or refuse (selection-and-edits.md)

on timeline select clip C:
  inspector.target = C
  if C.transcript_link is set:
    transcript.reveal(first word id still linked)

on timeline drag clip body by dt:
  move start_seconds by dt, clamped at 0
  if link_group is set and the modifier for "move group" is held:
    add dt to every clip in the group
  do not change source_in

on timeline drag clip end:
  ripple_trim_end

on timeline drag the cut between two adjacent clips:
  roll

on timeline drag inside a clip with the slip modifier:
  slip

on playhead change to t:
  preview.show(composite_frame(composition, t, captions_visible=true))
  transcript.scroll_to(word whose source time covers the mapped source clock)
  meters = meter(current audio block) per audible track and master

on inspector edit of CaptionStyle:
  write the field onto project.styles.by_id
  preview repaints captions
  the saved style is what burn-in will read

on inspector edit of gain, fade, pan, mute, filters, studio_sound:
  write AudioClipSettings
  if a studio_sound field changed: drop that effect's pcm cache

on export:
  export_composition(...)     # export-render.md
  burn_captions follows options.burn_captions, default false
  sidecars default true
```

Playhead follow uses the word whose `[start_seconds, end_seconds)` contains the source time under the playhead. Ignored words are skipped when choosing the follow target so the panel rests on a word that will play.

## Keyboard minimum

These actions must exist. The key bindings can match the platform. The actions cannot be only on a hidden menu.

| Action | Effect |
| --- | --- |
| Play / pause | Toggle transport |
| Ignore selection | `ignore_words` with reason `manual` |
| Restore selection | Clear `ignored`, re-apply timeline |
| Split at playhead | Two clips, same link_group, source_in split on the source clock |
| Delete clip | Ripple-remove the clip (later clips shift left by its duration) |

Delete clip is a timeline edit. It does not set `ignored` on the transcript. If the clip has a `transcript_link`, ask before deleting: "Remove this clip from the timeline" leaves the transcript flags as they are and drops the link.

## Extra wires

| Operator action | Call |
| --- | --- |
| Record voiceover at the playhead | [voiceover.md](voiceover.md) `record_voiceover` |
| Punch in over a selected range | `punch_in` on the voiceover track |
| Add image, video, or GIF | [overlays.md](overlays.md) `add_overlay` |
| Search stock | [stock-asset-providers.md](stock-asset-providers.md). Hidden when no provider key is configured |
| Record camera with background removed | [self-record-bg-remove.md](self-record-bg-remove.md) |
| Align two clips | [audio-waveform-align.md](audio-waveform-align.md), then `switch_angle` |

The inspector shows attribution on a stock clip and the duck-under-dialogue toggle on a voiceover track.

## What this surface does not include

A second monitor layout, comments, live collaboration, a Descript-shaped toolbar, or pixel measurements. Green screen, eye contact, and voice clone have no controls here.

## Errors shown in the surface

| Case | What the operator sees |
| --- | --- |
| Style field rejected (caption-style.md) | The inspector keeps the previous value and shows the reject reason |
| Studio Sound fallback | Inspector shows the backend that ran |
| Burn-in failed, mux kept | Export result links the unburned file and the error |
| Restore refused after a roll | A confirm step, not a silent no-op |
