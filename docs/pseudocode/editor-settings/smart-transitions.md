# Smart transitions on new scenes

## Input / output

```text
input:   composition with scenes (cards), each with layers; user.defaults.smart_transitions
output:  on scene add: transition records on the new boundary
         at playback/export: temporary keyframe cues that morph matching layers across each smart boundary
```

## On scene add

```text
DEFAULT_SMART = { effect: "smart", params: {fade_unmatched: true}, duration: 0.2, cross: true,
                  curve: "ease-in-and-out" }

hook after_add_scene_boundary(project, comp, boundary):     # script break, timeline, and agent tools
  if not user.defaults.smart_transitions: return
  scene = scene_starting_at(comp, boundary)
  if scene == null: return
  b = boundary_before(scene)
  if b.head_transition == null: b.head_transition = DEFAULT_SMART   # incoming side
  if b.tail_transition == null: b.tail_transition = DEFAULT_SMART   # outgoing side
  log transition_added{origin: "smart_transition", is_auto_added: true}
```

## Bake for playback

```text
function bake_smart_transitions(comp) -> (cues, extend_layer_ids):
  if not comp.has_video_metadata: return ([], {})
  cues = []
  for (A, B) in consecutive(comp.scenes):
    out = A.end_boundary.tail_transition; inn = B.start_boundary.head_transition
    if not (is_smart(out) and is_smart(inn)): continue
    d     = abs(out.duration)                              # 0.2
    start = A.end - d; total = 2 * d                       # 0.4 s centered on the cut
    curve = out.curve
    pairs = pair_layers(A, B, comp.fps)

    for (a, b) in pairs:
      if a.ends_at_boundary and b.starts_at_boundary:
        props = {}
        for p in ANIMATABLE_PROPS:
          if has_user_animation(a, p, start, total) or has_user_animation(b, p, start, total): continue
          va = held_value(a, p, at = A.end); vb = value(b, p, at = B.start)
          if p == corner_radius: va = clamp_radius(va, a.size); vb = clamp_radius(vb, b.size)
          if va != vb: props[p] = (va, vb)
        if props: cues += tween_cue(layers = [a, b], from = start, length = total, props, curve)

    if out.params.fade_unmatched:
      for a in A.layers - pairs.left  where a.ends_at_boundary:   cues += fade(a, out,  A.end - d, d, safe(curve))
      for b in B.layers - pairs.right where b.starts_at_boundary: cues += fade(b, in_, B.start,    d, safe(curve))

    cues += tween_scene_effects(A, B, start, total, curve)  # backgrounds etc., centered on B.start
  if is_smart(last(comp.scenes).end_boundary.tail_transition):
    fade_out_boundary_layers(last scene)
  return (cues, layers_extended_past_their_scene(cues))

function pair_layers(A, B, fps) -> [(a, b)]:
  used = {}; pairs = []
  for a in visible(A.layers) ordered (same-source first):
    b = B.layer_with_source(a.source)                         # avatar id | track id
    if b == null and not a.is_avatar:
      b = first b' in visible(B.layers) - used where
            b'.track_type == a.track_type and
            (a.track_type != "vector" or b'.first_visual_type == a.first_visual_type) and
            b'.track_name == a.track_name and
            frame(a.end, fps) == frame(A.end, fps) and frame(b'.start, fps) == frame(B.start, fps)
    if b: used += b; pairs += (a, b)
  return pairs

safe(curve) = { out-elastic: out-quint, out-bounce: out-quart, out-back: out-quad,
                in-back: in-quad, in-out-back: in-out-quad }[curve] or curve
```

The renderer treats an interior smart boundary as a hard cut plus these cues. The first or last smart boundary renders as a fade.
