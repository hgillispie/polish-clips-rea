# Apply Smart transitions to new scenes

> **Signed-in result (2026-10-22, observed-network):** neither the agent's `add_scene_boundaries` nor a manual Split scene added a Smart transition in Hunter's project. Whether his local pref was off is unknown. An explicit crossfade is stored as `videoFades` with type `com.descript.crossFadeTransition`. Details: [signed-in-gaps.md](signed-in-gaps.md).

## Keys and defaults (decompiled)

| Layer | Key | Default |
| --- | --- | --- |
| Local preference (app-wide) | `Application.applySmartTransitions` | `undefined`, read as **on** (`undefined || value`) |
| Project | none | The toggle has no per-project override |
| Result in the document | each scene boundary's `headTransitionEffect` / `tailTransitionEffect` of type `com.descript.smartTransition`, with `fadeInDuration` / `fadeOutDuration` and `headCurve` / `tailCurve` | n/a |
| Effect parameter | `FadeUnmatched` (index 0, UI "Add fades") | `1` (on) |

Toggling it in Preferences logs `settings_toggle_apply_smart_transitions {is_enabled}` and persists the pref. The info tooltip reads: "Matching elements across scenes will animate seamlessly for a polished, professional look." No feature flag gates it.

## What counts as a new scene (decompiled)

Descript's "scenes" are cards separated by **card boundaries**. The auto-add listens for exactly two actions:

| Action | Typical origin |
| --- | --- |
| `ADD_CARD_BOUNDARY_AT_TEXT_LOCATION` | Adding a scene break in the script at the cursor (origin labels **inferred**; the action is dispatched from several script and context-menu sagas) |
| `ADD_CARD_BOUNDARY_AT_TIME_OFFSET` | Adding a scene from the timeline at a time (**inferred** origin) |

After the reducer has inserted the boundary, the listener finds the scene that **starts** at that location and, if the pref is on, adds the transition to that new scene's start boundary. Scenes created any other way do not get one automatically: layout application, imports, templates, duplicating a composition, and (not traced) the agent's `add_scene_boundaries` tool, which edits the document directly (**inferred**; see the gaps file).

## Which transition, how long, which easing (decompiled)

```text
effect   = new com.descript.smartTransition with its default preset ([FadeUnmatched = 1])
duration = 0.2 s per side, stored as -0.2 (negative = a "cross" transition straddling the boundary)
curve    = "ease-in-and-out" (the global default animation curve)
```

- It ignores the "last used transition" memory that the manual transition picker uses. The auto-add always uses these defaults.
- It writes the head side (incoming scene, `fadeInDuration`, `headCurve`) and the tail side (outgoing scene, `fadeOutDuration`, `tailCurve`) separately, and **skips a side that already has a transition**. A user-set transition is never overwritten.
- It logs `transition_added {target: "scene", kind: "visual", is_cross: true, curve, is_auto_added: true, origin: "smart_transition"}`.

Curve values available to transitions: ease-in-and-out (default), ease-in, ease-out, ease-in/out quad, quart, quint, elastic, bounce, back, and linear. When a curve drives an opacity fade (see below), the overshooting ones are mapped to safe ones: out-elastic → out-quint, out-bounce → out-quart, out-back → out-quad, in-back → in-quad, in-out-back → in-out-quad.

## What a Smart transition does at playback (decompiled)

A Smart transition is not a pixel transition (crossfade, wipe). It is "magic move": just before playback and export, the client **bakes temporary animation cues** that tween matching layers from their outgoing-scene state to their incoming-scene state. That pass runs only for storyboard (new document model) compositions with video metadata, and its failures are reported under "smart-transitions" without breaking playback.

For each consecutive pair of scenes (outgoing A, incoming B) where A's out-transition and B's in-transition are both Smart:

1. **Timing.** `start = A.end − |d|`, `total = 2·|d|`, where `d` is A's out-transition duration. With the default that is **0.4 s centered on the cut**.
2. **Pair layers.** Visible layers are keyed by their source: avatar id, sequence track id, or source track id. A layer in A pairs with the layer in B from the **same source**. If none, it pairs with an unused B layer of the **same track type** (and, for vector layers, the same first visual type: text, shape, title…) and the **same track name**, provided the A layer **ends exactly at the boundary** and the B layer **starts exactly at it**. "Exactly" means the same frame at the composition's frame rate.
3. **Tween matched pairs.** For every property in the client's animatable-effect list (we did not enumerate it; it is the same list keyframe animations use) whose value differs between A's held end state and B's start state, two keyframes go from A's value at `t = 0` to B's value at `t = total` using A's tail curve. The cue is attached to both layers. Corner radius is clamped to half the smaller side. A property is skipped if either layer already has a user animation or an in/out transition covering that window, so the user's animation wins.
4. **Unmatched layers.** If `FadeUnmatched` is on (default), an A layer with no partner that ends at the boundary fades **out** (opacity to 0), and a B layer with no partner that starts at the boundary fades **in** (from 0). Each fade takes `|d|` (0.2 s), with the mapped curve. With it off, they cut.
5. **Scene-level effects.** Effects on the scene card itself (backgrounds and so on) that exist on both sides with different values are tweened the same way. The incoming one is centered on B's start: `B.start ± total/2`.
6. **Last scene.** If the final scene has a Smart out-transition, its boundary-ending layers fade out.
7. **Native engine.** The rendering worker treats an interior Smart transition as "no transition" (the baked cues do the work). On the first or last transition it renders `{kind: "smart", fade_unmatched}`, effectively a fade.

When baked cues extend a layer slightly past its scene, the layer ids are returned as `extendCardLayerIds` so the renderer keeps them alive through the window.
