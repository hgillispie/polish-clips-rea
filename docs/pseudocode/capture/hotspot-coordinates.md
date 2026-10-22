# Hotspot coordinates

Evidence: **decompiled** (background `getClickPos`; web `parseExtensionCapture` adjusts tab size).

Hotspot `x`, `y` are stored **normalized to the screenshot**, 0..1, top-left origin,
pointing at the click centre. Width/height of the hotspot are pixels at a reference
size (40×40 default for pulsating hotspots; HOTSPOT_SIZE 80 is the editor's default
for new ones).

```
getClickPos(click, tab, frame):
  # positions in screen CSS px
  absX = frame.frameScreenX - tab.tabScreenX + click.frameX
  absY = frame.frameScreenY - tab.tabScreenY + click.frameY
  return { x: absX / tab.tabWidth, y: absY / tab.tabHeight }
```

Same transform normalizes `clickContext.originalRect` into `rectContext`
(sent to the AI image endpoint so it can see what was clicked).

## Zoomed / mismatched tabs (web side)

Before computing, the step builder sanity-checks tab size against the page context:

```
fixTab(tab, pageContext):
  ratio(a,b) = max(a/b, b/a)
  w = ratio(tab.tabWidth, pageContext.width)  > 1.5 ? pageContext.width  : tab.tabWidth
  h = ratio(tab.tabHeight, pageContext.height) > 1.5 ? pageContext.height : tab.tabHeight
```

This guards browser zoom / devicePixelRatio mismatches between what the
background measured and what the page reported.

## Rendering (player)

`left = x * stageWidth - hotspotWidth/2`, `top = y * stageHeight - hotspotHeight/2`
(inferred from usage; the player keeps a 10 px edge buffer, `HOTSPOT_EDGE_BUFFER`,
when placing callouts).
