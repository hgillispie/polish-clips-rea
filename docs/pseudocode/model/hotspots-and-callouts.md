# Hotspots and callouts

Evidence: **decompiled** (type guards, player components), **observed** (hotspot keys).

```
Hotspot {
  id
  x, y                         # 0..1 normalized centre on the image (capture/hotspot-coordinates.md)
  width, height                # px at reference size (40 default from capture; 80 editor default)
  style: "pulsating" (default) | "callout" | "area"
  label                        # rich text; may contain {{variables}}
  defaultOpen: bool            # tooltip shown without hover
  hideButton?: bool            # callout without "Next" button ("Callouts without Button" flag)
  preferredDirection?          # tooltip placement preference
  calloutArrowDirection?: "none" | up/down/left/right…   # callouts only
  shape?: "rounded" | …        # "Callout Shape" flag
  bgColor, textColor, borderColor?, overlayColor?   # overlayColor: dim the rest (area/spotlight)
  targetId?                    # step to go to on click (branching); absent = next step
  pathType?: "step" | "url" | "crossFlow"; url?, openInTheSameTab?, targetFlowId?, targetStepId?
  syncTextToVoiceover?: bool   # caption text follows synthetic voice timepoints
}
```

Hotspots live on Image steps; observed public flows also carry callouts on Video steps (shown while the clip plays).

Classification:
- `isHotspot(h)` ⇔ `style != "callout"` (pulsating dot or area box; clickable target).
- Callout with arrow / without arrow decided by `calloutArrowDirection` (missing or "none" = without).
- Animation order on step enter: hotspots first, then callouts with arrow, then callouts
  without arrow (decompiled ordering helper).
- `filterValidHotspots`: drop negative coordinates.

Rendering (decompiled player):
- Pulsating hotspot = inner + outer circle; when pan-zoom is active, scale = 1/zoomLevel
  so the dot stays the same on-screen size (hover 1.2/zoomLevel).
- Hover/click spring: stiffness 600, damping 16.
- Tooltip keeps a 10 px edge buffer inside the stage.
- Clicking a hotspot: url → open (new tab unless openInTheSameTab and not embedded);
  crossFlow → load other flow at targetStepId; otherwise navigate to `targetId` or next
  non-empty step; report `Hotspot Clicked {stepId, hotspotId, hotspotLabel, targetStepId|"Unassigned"}`.

AI copy: `POST /api/ai/flow-hotspots {…options, flowId, promptId}` → `{hotspots:[{id,label}], promptId}`;
labels "-" mean empty. Refinements chain via `promptId`. "Delete all hotspot text" clears
labels and `syncTextToVoiceover`. Tone/use case: promotional, educational, sales, custom. (decompiled)
